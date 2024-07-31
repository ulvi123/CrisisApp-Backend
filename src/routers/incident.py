from fastapi import APIRouter, Request, HTTPException, Header, status, Depends
from sqlalchemy.orm import Session
from src import models
from src import schemas
from src.database import get_db
from src.utils import (
    verify_slack_request,
    create_modal_view,
    load_options_from_file,
    slack_challenge_parameter_verification,
)
from starlette.responses import JSONResponse
from config import get_settings,Settings
import requests
import json
from pydantic import ValidationError
from datetime import datetime
from src.helperFunctions.opsgenie import create_alert
from src.helperFunctions.jira import create_jira_ticket
from src.helperFunctions.slack_utils import post_message_to_slack, create_slack_channel
import logging



logger = logging.getLogger(__name__)
router = APIRouter()


# Load options at application startup
options = load_options_from_file("options.json")



@router.post("/slack/commands")
async def incident(
    request: Request,
    x_slack_request_timestamp: str = Header(None),
    x_slack_signature: str = Header(None),
    settings: Settings = Depends(get_settings)
):
    
    headers = request.headers
    logger.debug("Headers received:")
    for key, value in headers.items():
        logger.debug(f"{key}: {value}")
    
    # Then proceed with request verification
    try:
        body = await request.body()
        await verify_slack_request(
            body, x_slack_signature, x_slack_request_timestamp
        )
    except Exception as e:
        logger.error(f"Error verifying request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    
    # Handle URL verification first
    try:
        json_body = json.loads(body.decode('utf-8'))
        if json_body.get("type") == "url_verification":
            logger.debug("URL verification received")
            return {"challenge": json_body.get("challenge")}
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON body")
           
    # Process form data
    try:
        form_data = await request.form()
        logger.debug("Form data received:")
        for key, value in form_data.items():
            logger.debug(f"{key}: {value}")
    except Exception as e:
        logger.error(f"Error parsing form data: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Failed to parse form data: {str(e)}"
        ) from e

    for key, value in form_data.items():
        print(f"{key}: {value}")

    # Verify token
    token = form_data.get("token")
    command = form_data.get("command")
    trigger_id = form_data.get("trigger_id")
    
    logger.debug(f"Received token: {token}")
    logger.debug(f"Configured token: {settings.SLACK_VERIFICATION_TOKEN}")

    if token != settings.SLACK_VERIFICATION_TOKEN:
        logger.error("Invalid token")
        raise HTTPException(status_code=400, detail="Invalid token")

    if command == "/create-incident":
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"
        }
        modal_view = await create_modal_view(
            callback_id="incident_form"
        )
        payload = {"trigger_id": trigger_id, "view": modal_view}
        logger.debug(json.dumps(payload, indent=2))

        try:
            slack_response = requests.post(
                "https://slack.com/api/views.open",
                headers=headers,
                json=payload,
                timeout=2
            )
            slack_response.raise_for_status()  # Raise an exception for HTTP errors
            slack_response_data = slack_response.json()  # Parse JSON response

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to open the form: {str(e)}"
            ) from e
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to parse Slack response: {str(e)}"
            ) from e

        if not slack_response_data.get("ok"):
            raise HTTPException(
                status_code=400, detail=f"Slack API error: {slack_response_data}"
            )

        return JSONResponse(
            status_code=200,
            content={
                "response_type": "ephemeral",
                "text": "Incident form opening executed successfully in the fastapi Backend",
            },
        )
  
    return JSONResponse(status_code=404, content={"detail": "Command not found"})


@router.post("/slack/interactions")
async def slack_interactions(
    request: Request,
    db: Session = Depends(get_db),
    x_slack_signature: str = Header(None),
    x_slack_request_timestamp: str = Header(None),
    settings: Settings = Depends(get_settings)
):
    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse request body: {str(e)}"
        ) from e

    await verify_slack_request(request, x_slack_signature, x_slack_request_timestamp)

    token = payload.get("token")

    if token != settings.SLACK_VERIFICATION_TOKEN:
        raise HTTPException(status_code=400, detail="Invalid token")

    # Processing the actual interaction based on the propagated event
    if payload.get("type") == "view_submission":
        callback_id = payload.get("view", {}).get("callback_id")
        if callback_id == "incident_form":
            try:
                state_values = (
                    payload.get("view", {}).get("state", {}).get("values", {})
                )
                print("State values:", json.dumps(state_values, indent=2))

                # Extracting and converting the start_time and end_time
                start_date = (
                    state_values.get("start_time", {})
                    .get("start_date_action", {})
                    .get("selected_date")
                )
                start_time = (
                    state_values.get("start_time_picker", {})
                    .get("start_time_picker_action", {})
                    .get("selected_time")
                )
                end_date = (
                    state_values.get("end_time", {})
                    .get("end_date_action", {})
                    .get("selected_date")
                )
                end_time = (
                    state_values.get("end_time_picker", {})
                    .get("end_time_picker_action", {})
                    .get("selected_time")
                )

                if not start_date or not start_time:
                    raise HTTPException(
                        status_code=400, detail="Missing start datetime"
                    )
                if not end_date or not end_time:
                    raise HTTPException(status_code=400, detail="Missing end datetime")

                # Combine date and time strings
                start_datetime_str = f"{start_date}T{start_time}:00"
                end_datetime_str = f"{end_date}T{end_time}:00"

                # Exception handling
                try:
                    start_time_obj = datetime.strptime(
                        start_datetime_str, "%Y-%m-%dT%H:%M:%S"
                    )
                    end_time_obj = datetime.strptime(
                        end_datetime_str, "%Y-%m-%dT%H:%M:%S"
                    )
                except ValueError:
                    raise HTTPException(
                        status_code=400, detail="Invalid datetime format"
                    ) from e

                # Extracting values from the Slack payload
                affected_products_options = (
                    state_values.get("affected_products", {})
                    .get("affected_products_action", {})
                    .get("selected_options", [])
                )
                affected_products = [
                    option["value"] for option in affected_products_options
                ]

                suspected_owning_team_options = (
                    state_values.get("suspected_owning_team", {})
                    .get("suspected_owning_team_action", {})
                    .get("selected_options", [])
                )
                suspected_owning_team = [
                    option["value"] for option in suspected_owning_team_options
                ]

                suspected_affected_components_options = (
                    state_values.get("suspected_affected_components", {})
                    .get("suspected_affected_components_action", {})
                    .get("selected_options", [])
                )
                suspected_affected_components = [
                    option["value"] for option in suspected_affected_components_options
                ]

                # severity = state_values.get("severity", {}).get("severity_action", {}).get("selected_options", [])
                # # Extracting severity from state_values
                # # severity = state_values.get("severity", {}).get("severity_action", {}).get("selected_option", {}).get("value", "")
                # severity = [option["value"] for option in severity]

                print(
                    f"Extracted values: {affected_products} {suspected_owning_team} {suspected_affected_components}"
                )

                # Print for debugging
                print(f"Processed Affected Products: {affected_products}")
                print(f"Processed Suspected Owning Team: {suspected_owning_team}")
                print(
                    f"Processed Suspected Affected Components: {suspected_affected_components}"
                )
                print("Extracted values:", affected_products, suspected_owning_team)

                incident_data = {
                    "affected_products": affected_products,
                    "severity": "",
                    "suspected_owning_team": suspected_owning_team,
                    "start_time": start_time_obj.isoformat(),
                    "end_time": end_time_obj.isoformat(),
                    "p1_customer_affected": any(
                        option.get("value") == "p1_customer_affected"
                        for option in state_values.get("p1_customer_affected", {})
                        .get("p1_customer_affected_action", {})
                        .get("selected_options", [])
                    ),
                    "suspected_affected_components": suspected_affected_components,
                    "description": state_values.get("description", {})
                    .get("description_action", {})
                    .get("value"),
                    "message_for_sp": state_values.get("message_for_sp", {})
                    .get("message_for_sp_action", {})
                    .get("value", ""),
                    "statuspage_notification": any(
                        option.get("value") == "statuspage_notification"
                        for option in state_values.get(
                            "flags_for_statuspage_notification", {}
                        )
                        .get("flags_for_statuspage_notification_action", {})
                        .get("selected_options", [])
                    ),
                    "separate_channel_creation": any(
                        option.get("value") == "separate_channel_creation"
                        for option in state_values.get(
                            "flags_for_statuspage_notification", {}
                        )
                        .get("flags_for_statuspage_notification_action", {})
                        .get("selected_options", [])
                    ),
                }

                print(
                    "Incident data:", json.dumps(incident_data, indent=4)
                )  # Log the incident data for debugging

                try:
                    incident = schemas.IncidentCreate(**incident_data)
                    print(f"Incident data after parsing: {incident}")
                except ValidationError as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to parse request body: {str(e)}",
                    )
                # Log the parsed incident data fields
                print("Incident data before Jira ticket creation:")
                print(f"Affected Products: {incident.affected_products}")
                print(f"Suspected Owning Team: {incident.suspected_owning_team}")
                print(
                    f"Suspected Affected Components: {incident.suspected_affected_components}"
                )

            except ValidationError as e:
                raise HTTPException(
                    status_code=400, detail=f"Failed to parse request body: {str(e)}"
                )

            # Time to save the incident to our postgresql database
            db_incident = models.Incident(**incident.dict())
            db.add(db_incident)
            db.commit()
            db.refresh(db_incident)

            # Slack channel creation integration here
            try:
                channel_name = f"incident-{db_incident.suspected_owning_team[0].replace( ' ', '-' ).lower()}"
                channel_id = await create_slack_channel(channel_name)
                print(f"New Slack channel created with ID: {channel_id}")

                # Posting a message to the created channel
                incident_message = f"New Incident Created:\n\n*Description:* {db_incident.description}\n*Severity:* {db_incident.severity}\n*Affected Products:* {', '.join(db_incident.affected_products)}\n*Start Time:* {db_incident.start_time}\n*End Time:* {db_incident.end_time}\n*Customer Affected:* {'Yes' if db_incident.p1_customer_affected else 'No'}\n*Suspected Owning Team:* {', '.join(db_incident.suspected_owning_team)}"
                await post_message_to_slack(channel_id, incident_message)

                # Posting message to general channel
                general_outages_message = f"New Incident Created in #{channel_name}:\n\n*Description:* {db_incident.description}\n*Severity:* {db_incident.severity}\n*Affected Products:* {', '.join(db_incident.affected_products)}\n*Start Time:* {db_incident.start_time}\n*End Time:* {db_incident.end_time}\n*Customer Affected:* {'Yes' if db_incident.p1_customer_affected else 'No'}"
                await post_message_to_slack(
                    settings.SLACK_GENERAL_OUTAGES_CHANNEL, general_outages_message
                )

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
                )

            # Log the incident data for debug print statements here
            print(f"Incident data before Jira ticket creation:")
            print(f"Affected Products: {db_incident.affected_products}")
            print(f"Suspected Owning Team: {db_incident.suspected_owning_team}")
            print(
                f"Suspected Affected Components: {db_incident.suspected_affected_components}"
            )
            print(f"End Time: {db_incident.start_time}")

            if db_incident.end_time is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="End time not found"
                )

            try:
                await create_alert(db_incident)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
                )

            # Jira integration
            try:
                issue = create_jira_ticket(db_incident)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
                )
            return {"incident_id": db_incident.id, "issue_key": issue["key"]}

        else:
            return JSONResponse(
                status_code=404, content={"detail": "Command or callback ID not found"}
            )

    return JSONResponse(content={"response_action": "clear"})

    return JSONResponse(status_code=404, content={"detail": "Event type not found"})
