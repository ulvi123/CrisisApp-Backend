from fastapi import APIRouter, Request, Response, HTTPException, Header, status, Depends
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
from src.helperFunctions.opsgenie import create_alert
from src.helperFunctions.jira import create_jira_ticket
from src.utils import load_options_from_file

router = APIRouter()

# Load options at application startup
options = load_options_from_file("options.json")


@router.post("/slack/commands")
async def incident(
    request: Request,
    x_slack_request_timestamp: str = Header(None),
    x_slack_signature: str = Header(None),
):
    headers = request.headers
    print("Headers received:")
    for key, value in headers.items():
        print(f"{key}: {value}")

    try:
        await verify_slack_request(
            request, x_slack_signature, x_slack_request_timestamp
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    try:
        form_data = await request.form()
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse form data: {str(e)}"
        )
        
    print("Form data received:")
    for key, value in form_data.items():
        print(f"{key}: {value}")
    

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
        modal_view = await create_modal_view(callback_id="incident_form", options=options)
        payload = {"trigger_id": trigger_id, "view": modal_view}
        print(json.dumps(payload, indent=2))  # Log the payload for debugging

        try:
            slack_response = requests.post(
                "https://slack.com/api/views.open", headers=headers, json=payload, timeout=5
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

@router.post("/slack/interactions")
async def slack_interactions(
    request: Request,
    db:Session = Depends(get_db),
    x_slack_signature: str = Header(None),
    x_slack_request_timestamp: str = Header(None),
):
    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse request body: {str(e)}"
        )

    await verify_slack_request(request, x_slack_signature, x_slack_request_timestamp)

    token = payload.get("token")

    if token != settings.SLACK_VERIFICATION_TOKEN:
        raise HTTPException(status_code=400, detail="Invalid token")

    if payload.get("type") == "view_submission":
        try:
            state_values = payload.get("view", {}).get("state", {}).get("values", {})
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

            print(f"Extracted start_date: {start_date}, start_time: {start_time}")
            print(f"Extracted end_date: {end_date}, end_time: {end_time}")

            if not start_date or not start_time:
                raise HTTPException(status_code=400, detail="Missing start datetime")
            if not end_date or not end_time:
                raise HTTPException(status_code=400, detail="Missing end datetime")

            start_datetime_str = f"{start_date}T{start_time}:00"
            end_datetime_str = f"{end_date}T{end_time}:00"

            print(f"Combined start_datetime_str: {start_datetime_str}")
            print(f"Combined end_datetime_str: {end_datetime_str}")

            try:
                start_time_obj = datetime.strptime(
                    start_datetime_str, "%Y-%m-%dT%H:%M:%S"
                )
                end_time_obj = datetime.strptime(end_datetime_str, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid datetime format")

            print(f"Parsed start_time_obj: {start_time_obj}")
            print(f"Parsed end_time_obj: {end_time_obj}")

            affected_products_options = state_values.get("affected_products", {}).get("affected_products_action", {}).get("selected_options", [])
            affected_products = [option["value"] for option in affected_products_options]

            suspected_owning_team_options = state_values.get("suspected_owning_team", {}).get("suspected_owning_team_action", {}).get("selected_options", [])
            suspected_owning_team = [option["value"] for option in suspected_owning_team_options]

            suspected_affected_components_options = state_values.get("suspected_affected_components", {}).get("suspected_affected_components_action", {}).get("selected_options", [])
            suspected_affected_components = [option["value"] for option in suspected_affected_components_options]

            severity_options = state_values.get("severity", {}).get("severity_action", {}).get("selected_options", [])
            severity = [option["value"] for option in severity_options]

            incident_data = {
                "affected_products": affected_products,
                "severity": severity,
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
                "description": (
                    state_values.get("description", {})
                    .get("description_action", {})
                    .get("value")
                ),
                "message_for_sp": (
                    state_values.get("message_for_sp", {})
                    .get("message_for_sp_action", {})
                    .get("value", "")
                ),
                "statuspage_notification": any(
                    option.get("value") == "statuspage_notification"
                    for option in state_values.get("flags_for_statuspage_notification", {})
                    .get("flags_for_statuspage_notification_action", {})
                    .get("selected_options", [])
                ),
                "separate_channel_creation": any(
                    option.get("value") == "separate_channel_creation"
                    for option in state_values.get("flags_for_statuspage_notification", {})
                    .get("flags_for_statuspage_notification_action", {})
                    .get("selected_options", [])
                ),
            }

            print("Incident data:", json.dumps(incident_data, indent=4))

            incident = schemas.IncidentCreate(**incident_data)

            db_incident = models.Incident(**incident.model_dump())
            db.add(db_incident)
            db.commit()
            db.refresh(db_incident)

            if db_incident.end_time is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="End time not found")

            try:
                await create_alert(db_incident)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

            try:
                issue = create_jira_ticket(db_incident)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e)
                )
            return {"issue_key": issue['key']}

        except ValidationError as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to parse request body: {str(e)}"
            )

        return JSONResponse(content={"response_action": "clear"})

    return JSONResponse(status_code=404, content={"detail": "Event type not found"})
