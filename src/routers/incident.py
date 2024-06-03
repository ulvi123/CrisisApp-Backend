from fastapi import APIRouter, Request, Response, HTTPException, Header, status, Depends
import os
from sqlalchemy.orm import Session
from src import models
from src import schemas
from src.database import get_db
from src.utils import verify_slack_request, create_modal_view
from starlette.responses import JSONResponse
from src.config import settings
import requests
import json
from pydantic import ValidationError
from datetime import datetime


router = APIRouter()


# Endpoint to handle slash commands
@router.post("/slack/commands")
async def incident(
    request: Request,
    x_slack_request_timestamp: str = Header(None),
    x_slack_signature: str = Header(None),
):
    # Debugging statement to check header values
    headers = request.headers
    print("Headers received:")
    for key, value in headers.items():
        print(f"{key}: {value}")

    # Verify Slack request signature
    try:
        await verify_slack_request(
            request, x_slack_signature, x_slack_request_timestamp
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Parse form data
    try:
        form_data = await request.form()
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse form data: {str(e)}"
        )

    # Handle URL verification
    if form_data.get("type") == "url_verification":
        return {"challenge": form_data.get("challenge")}

    token = form_data.get("token")
    if token != settings.SLACK_VERIFICATION_TOKEN:
        raise HTTPException(status_code=400, detail="Invalid token")

    command = form_data.get("command")
    trigger_id = form_data.get("trigger_id")

    if command == "/create-incident":
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        }
        modal_view = await create_modal_view(callback_id="incident_form")
        payload = {"trigger_id": trigger_id, "view": modal_view}
        print(json.dumps(payload, indent=2))  # Log the payload for debugging
        try:
            slack_response = requests.post(
                "https://slack.com/api/views.open", headers=headers, json=payload
            )
            slack_response.raise_for_status()  # Raise an exception for HTTP errors
            slack_response_data = slack_response.json()  # Parse JSON response
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to open the form: {str(e)}"
            )
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to parse Slack response: {str(e)}"
            )

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
    else:
        return JSONResponse(status_code=404, content={"detail": "Command not found"})


# Endpoint to handle interactivity when sending the post back to the server from slack
@router.post("/slack/interactions", status_code=status.HTTP_201_CREATED)
async def slack_interactions(
    request: Request,
    db: Session = Depends(get_db),
    x_slack_signature: str = Header(None),
    x_slack_request_timestamp: str = Header(None),
):
    # Verify Slack request
    await verify_slack_request(request, x_slack_signature, x_slack_request_timestamp)

    # Parse form data
    try:
        form_data = await request.form()
        payload = form_data.get("payload")
        if not payload:
            raise HTTPException(
                status_code=400, detail="Payload is missing in the request"
            )
        payload_data = json.loads(payload)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse request body: {str(e)}"
        )

    # Validate the token
    token = payload_data.get("token")
    if token != settings.SLACK_VERIFICATION_TOKEN:
        raise HTTPException(status_code=400, detail="Invalid token")

    # Processing the actual interaction based on the propagated event
    if payload_data.get("type") == "view_submission":
        callback_id = payload_data.get("view", {}).get("callback_id")
        if callback_id == "incident_form":
            try:
                state_values = (
                    payload_data.get("view", {}).get("state", {}).get("values", {})
                )
                print("State values:", json.dumps(state_values, indent=2))

                # Extracting  and converting the start_time
                start_time_str = state_values.get("start_time", {}).get("start_time_action", {}).get("value")
                print("Extracted start_time_str:", start_time_str)  # Debug start_time_str
                if start_time_str is None:
                    raise HTTPException(status_code=400, detail="Missing start time")

                try:
                    start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S')  # Adjust the format as needed
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid start time format")

                # Building the incident object
                incident_data = {
                    "affected_products": state_values.get("affected_products", {})
                    .get("affected_products_action", {})
                    .get("selected_option", {})
                    .get("value"),
                    "severity": state_values.get("severity", {})
                    .get("severity_action", {})
                    .get("selected_option", {})
                    .get("value"),
                    "suspected_owning_team": state_values.get(
                        "suspected_owning_team", {}
                    )
                    .get("suspected_owning_team_action", {})
                    .get("selected_options", [{}])[0]
                    .get("value"),
                    "start_time": start_time.isoformat(),  # Convert datetime to string
                    "p1_customer_affected": "p1_customer_affected"
                    in [
                        option.get("value")
                        for option in state_values.get("p1_customer_affected", {})
                        .get("p1_customer_affected_action", {})
                        .get("selected_options", [])
                    ],
                    "suspected_affected_components": state_values.get(
                        "suspected_affected_components", {}
                    )
                    .get("suspected_affected_components_action", {})
                    .get("selected_option", {})
                    .get("value"),
                    "description": state_values.get("description", {})
                    .get("description_action", {})
                    .get("value"),
                    "message_for_sp": state_values.get("message_for_sp", {})
                    .get("message_for_sp_action", {})
                    .get("value", ""),
                    "statuspage_notification": "statuspage_notification"
                    in [
                        option.get("value")
                        for option in state_values.get(
                            "flags_for_statuspage_notification", {}
                        )
                        .get("flags_for_statuspage_notification_action", {})
                        .get("selected_options", [])
                    ],
                    "separate_channel_creation": "separate_channel_creation"
                    in [
                        option.get("value")
                        for option in state_values.get(
                            "flags_for_statuspage_notification", {}
                        )
                        .get("flags_for_statuspage_notification_action", {})
                        .get("selected_options", [])
                    ],
                }

                print(
                    "Incident data:", json.dumps(incident_data, indent=2)
                )  # Log the incident data for debugging

                incident = schemas.IncidentCreate(**incident_data)

            except ValidationError as e:
                raise HTTPException(
                    status_code=400, detail=f"Failed to parse request body: {str(e)}"
                )

            # Time to save the incident to our postgre database
            db_incident = models.Incident(**incident.dict())
            db.add(db_incident)
            db.commit()
            db.refresh(db_incident)

            # Return the response to slack user in a form of a json
            return JSONResponse(
                status_code=201,
                content={
                    "response_type": "in_channel",
                    "text": "Incident created successfully",
                },
            )

        else:
            return JSONResponse(
                status_code=404, content={"detail": "Command or callback ID not found"}
            )

    return JSONResponse(status_code=404, content={"detail": "Event type not found"})
