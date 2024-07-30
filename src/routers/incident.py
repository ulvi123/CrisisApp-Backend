from fastapi import APIRouter, Request, Response, HTTPException, Header
import os
from src.utils import verify_slack_request, create_modal_view
from starlette.responses import JSONResponse
from src.config import settings
import requests
import json


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
        modal_view = await create_modal_view()
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
@router.post("/slack/interactions")
async def slack_interactions(
    request: Request,
    slack_signature: str = Header(None),
    slack_request_timestamp: str = Header(None),
):
    body = await request.body()
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse request body: {str(e)}"
        )

    # Verify Slack request
    await verify_slack_request(request, slack_signature, slack_request_timestamp)

    token = payload.get("token")

    if token != settings.SLACK_VERIFICATION_TOKEN:
        raise HTTPException(status_code=400, detail="Invalid token")

    if payload.get("type") == "view_submission":
        # Process the submitted modal data here
        print(payload)  # Log the payload for debugging
        return JSONResponse(content={"response_action": "clear"})

                # Extracting  and converting the start_time
                start_time_str = state_values.get("start_time", {}).get("start_time_action", {}).get("value")
                print("Extracted start_time_str:", start_time_str)  # Debug start_time_str
                if start_time_str is None:
                    raise HTTPException(status_code=400, detail="Missing start time")
                try:
                    start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S')  # Adjust the format as needed
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid start time format")

#     return JSONResponse(content={})


@router.post("/incidents")
def create_incident():
    return {"status": "success", "message": "Incident form processed successfully"}
