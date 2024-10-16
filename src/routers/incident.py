import logging
from fastapi import APIRouter, Request, HTTPException, Header, status, Depends
from sqlalchemy.orm import Session
from src import models
from src import schemas
from src.database import get_db
from src.utils import (
    verify_slack_request,
    create_modal_view,
    load_options_from_file,
    get_modal_view
)
from starlette.responses import JSONResponse
from config import get_settings, Settings
import requests
import json
from pydantic import ValidationError
from datetime import datetime
from src.helperFunctions.opsgenie import create_alert
from src.helperFunctions.jira import create_jira_ticket
from src.helperFunctions.slack_utils import post_message_to_slack, create_slack_channel

from urllib.parse import parse_qs
from pydantic import BaseModel, ValidationError
import time
from slack_sdk.errors import SlackApiError
from src.helperFunctions.helper import get_current_user
from src.models import UserToken


#Logging configuration
schemas.IncidentResponse.Config()
logging.basicConfig(
    level=logging.INFO,  # Set the level to DEBUG for more verbosity
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),  # Outputs logs to the console
        logging.FileHandler("app.log")  # Optionally log to a file
    ]
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Load options at application startup
options = load_options_from_file("options.json")

#create incident slack command
@router.post("/slack/commands")
async def handling_slash_commands(
    request: Request,
    x_slack_request_timestamp: str = Header(None),
    x_slack_signature: str = Header(None),
    settings: Settings = Depends(get_settings),
):

    headers = request.headers
    logger.debug("Headers received:")
    for key, value in headers.items():
        logger.debug(f"{key}: {value}")

    # Then proceed with request verification
    try:
        body = await request.body()
        await verify_slack_request(
            body, x_slack_signature, x_slack_request_timestamp, settings
        )
    except Exception as e:
        logger.error(f"Error verifying request: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Process form data
    try:
        form_data = await request.form()
        command = form_data.get("command")
        trigger_id = form_data.get("trigger_id")
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
    logger.debug(f"Received token: {token}")
    logger.debug(f"Configured token: {settings.SLACK_VERIFICATION_TOKEN}")
    
    if token != settings.SLACK_VERIFICATION_TOKEN:
        logger.error("Invalid token")
        raise HTTPException(status_code=400, detail="Invalid token")
    
    
    #Checking the main commands for handling slash requests in slack
    if command == "/get-incident":
        logger.info("Handling /get-incident command")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        }
        modal_view = await get_modal_view(callback_id="so_lookup_form")
        payload = {"trigger_id": trigger_id, "view": modal_view}
        logger.debug(json.dumps(payload, indent=2))

        try:
            slack_response = requests.post(
                "https://slack.com/api/views.open",
                headers=headers,
                json=payload,
                timeout=3,
            )
            slack_response.raise_for_status()  # Raise an exception for HTTP errors
            slack_response_data = slack_response.json()  # Parse JSON response
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to open the form: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to open the form: {str(e)}"
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Slack response: {str(e)}")
            raise HTTPException(
                status_code=400, detail=f"Failed to parse Slack response: {str(e)}"
            )

        if not slack_response_data.get("ok"):
            logger.error(f"Slack API error: {slack_response_data}")
            raise HTTPException(
                status_code=400, detail=f"Slack API error: {slack_response_data}"
            )

        return JSONResponse(
            status_code=200,
            content={
                "response_type": "ephemeral",
                "text": "Incident Lookup form has been opened successfully.",
            },
        )
     
    # Open the incident form
    elif command == "/create-incident":
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        }
        modal_view = await create_modal_view(callback_id="incident_form")
        payload = {"trigger_id": trigger_id, "view": modal_view}
        logger.debug(json.dumps(payload, indent=2))

        try:
            slack_response = requests.post(
                "https://slack.com/api/views.open",
                headers=headers,
                json=payload,
                timeout=2,
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

        








#get incident slack command
# @router.post("/slack/commands")
# async def get_incident(
#     request:Request,
#     x_slack_request_timestamp: str = Header(None),
#     x_slack_signature: str = Header(None),
#     settings:Settings=Depends(get_settings)
# ):
    
#     logger.debug("Received request to /slack/commands")
#     print("Received request to /slack/commands")

#     headers = request.headers
#     logger.debug("Headers received")
#     for key, value in headers.items():
#         logger.debug(f"{key}:{value}")
        
#     # Then proceed with request verification
#     try:
#         body = await request.body()
#         logger.debug(f"Request body:{body.decode("utf-8")}")
#         await verify_slack_request(
#             body, x_slack_signature, x_slack_request_timestamp, settings
#         )
#     except Exception as e:
#         logger.error(f"Error verifying request: {str(e)}")
#         raise HTTPException(status_code=400, detail=str(e)) from e
    
#     # Process form data
#     try:
#         form_data = await request.form()
#         logger.debug("Form data received:")
#         for key, value in form_data.items():
#             logger.debug(f"{key}: {value}")
#     except Exception as e:
#         logger.error(f"Error parsing form data: {str(e)}")
#         raise HTTPException(
#             status_code=400, detail=f"Failed to parse form data: {str(e)}"
#         ) from e


#     # Verify token
#     token = form_data.get("token")
#     command = form_data.get("command")
#     trigger_id = form_data.get("trigger_id")

#     logger.debug(f"Received token: {token}")
#     logger.debug(f"Configured token: {settings.SLACK_VERIFICATION_TOKEN}")
#     logger.debug(f"Received command: {command}")
#     logger.debug(f"Received trigger_id: {trigger_id}")


#     if token != settings.SLACK_VERIFICATION_TOKEN:
#         logger.error("Invalid token")
#         raise HTTPException(status_code=400, detail="Invalid token")
    
    
#     print(f"Received command: {command}")
#     #Opening the get incident modal
#     if command.lower() == "/lookup-for-incident":
#         logger.debug("Matched /lookup-for-incident")
#         if not trigger_id:
#             logger.error("Missing trigger_id in the request")
#             raise HTTPException(status_code=400, detail="Missing trigger_id")
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
#         }
#         modal_view = await get_modal_view(callback_id="so_lookup_form")
#         payload = {"trigger_id": trigger_id, "view": modal_view	}
#         logger.debug(f"Payload to open modal: {json.dumps(payload, indent=2)}")
    
#         try:
#             slack_response = requests.post(
#                 "https://slack.com/api/views.open",
#                 headers=headers,
#                 json=payload,
#                 timeout=10,
#             )
#             slack_response.raise_for_status()  # Raise an exception for HTTP errors
#             slack_response_data = slack_response.json()  # Parse JSON response
            
#             # Log the Slack response data for debugging
#             logger.debug(f"Slack response data: {json.dumps(slack_response_data, indent=2)}")
            
#             if not slack_response_data.get("ok"):
#                 error_detail = slack_response_data.get("error", "Unknown error")
#                 logger.error(f"Slack API error: {error_detail}")
#             if error_detail == "invalid_auth":
#                 logger.error("This could indicate an issue with the SLACK_BOT_TOKEN")
#             elif error_detail == "missing_scope":
#                 logger.error("The app might be missing required OAuth scopes")
#             raise HTTPException(
#                 status_code=400, detail=f"Slack API error: {error_detail}"
#             )
        
#         except requests.exceptions.Timeout:
#             logger.error("Request timed out")
#             raise HTTPException(
#                 status_code = status.HTTP_504_GATEWAY_TIMEOUT,detail="Request timed out"
#             )  
            

#         except requests.exceptions.RequestException as e:
#             raise HTTPException(
#                 status_code=400, detail=f"Failed to open the form: {str(e)}"
#             ) from e
#         except json.JSONDecodeError as e:
#             raise HTTPException(
#                 status_code=400, detail=f"Failed to parse Slack response: {str(e)}"
#             ) from e
            
#         return JSONResponse(
#             status_code=200,
#             content={
#                 "response_type": "ephemeral",
#                 "text": "incident Lookup  form opening executed successfully in the fastapi Backend",
#             },
#         )  
    
        
#     return JSONResponse(status_code=404, content={"detail": "Command not foundddd"})

















#Logic for fetching the incident







#submitting an incident
@router.post("/slack/interactions", status_code=status.HTTP_201_CREATED)
async def slack_interactions(
    request: Request,
    db: Session = Depends(get_db),
    x_slack_signature: str = Header(None),
    x_slack_request_timestamp: str = Header(None),
    settings: Settings = Depends(get_settings),
):
    body = await request.body()
    await verify_slack_request(
        body, x_slack_signature, x_slack_request_timestamp, settings
    )

    
    logging.info("Processing Slack interactions...")

    # Log headers to ensure they're received
    logging.info(f"x_slack_signature: {x_slack_signature}")
    logging.info(f"x_slack_request_timestamp: {x_slack_request_timestamp}")
    decoded_body = parse_qs(body.decode("utf-8"))
    logging.info(f"Decoded body: {decoded_body}")
    payload_str = decoded_body.get("payload", [None])[0]
    if not payload_str:
        logging.error("Missing payload in the request")
        raise HTTPException(status_code=400, detail="Missing payload")

    # Parsing the payload here
    try:
        payload = json.loads(payload_str)
        print(f"Payload: {json.dumps(payload, indent=2)}")
        logging.info(f"Parsed payload: {json.dumps(payload, indent=2)}")
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse payload: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Failed to parse request body: {str(e)}"
        ) from e

    # Verifying the signature
   
    token = payload.get("token")
    if token != settings.SLACK_VERIFICATION_TOKEN:
        logging.error("Invalid Slack verification token")
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
                state_values = (
                    payload.get("view", {}).get("state", {}).get("values", {})
                )
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

                severity_option = (
                    state_values.get("severity", {})
                    .get("severity_action", {})
                    .get("selected_option", {})
                )
                severity = severity_option.get("value") if severity_option else None
                severity = [severity] if severity else []
                so_number = state_values.get("so_number", {}).get("so_number_action", {}).get("value")
                

                print(
                    f"Extracted values: {affected_products} {suspected_owning_team} {suspected_affected_components}"
                )

                # Creating the incident data
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
                    so_number: so_number
                }

                try:
                    incident = schemas.IncidentCreate(**incident_data)
                except ValidationError as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Failed to parse request body: {str(e)}",
                    ) from e

            except ValidationError as e:
                raise HTTPException(
                    status_code=400, detail=f"Failed to parse request body: {str(e)}"
                ) from e

            # Time to save the incident to our postgresql database
            db_incident = models.Incident(**incident.dict())
            db.add(db_incident)
            db.commit()
            db.refresh(db_incident)

            # Alert integration with Opsgenie
            try:
                await create_alert(db_incident)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
                ) from e

            # Jira integration
            try:
                issue = await create_jira_ticket(incident)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
                ) from e

            # Slack channel creation integration here
            try:
                start_api_calls_time = time.time()
                channel_name = f"incident-{db_incident.suspected_owning_team[0].replace( ' ', '-' ).lower()}"
                channel_id = await create_slack_channel(channel_name)
                logger.info(f"New Slack channel created with ID: {channel_id}")
                logger.info(f"SLACK_GENERAL_OUTAGES_CHANNEL: {settings.SLACK_GENERAL_OUTAGES_CHANNEL}")


                # Posting a message to the created channel
                incident_message = f"🚨 *New Incident Created* 🚨:\n\n*Description:* {db_incident.start_time} > {db_incident.severity} > {db_incident.affected_products} Outage\n*Severity:* {db_incident.severity}\n*Affected Products:* {', '.join(db_incident.affected_products)}\n*Start Time:* {db_incident.start_time}\n*End Time:* {db_incident.end_time}\n*Customer Affected:* {'Yes' if db_incident.p1_customer_affected else 'No'}\n*Suspected Owning Team:* {', '.join(db_incident.suspected_owning_team)}"
                await post_message_to_slack(channel_id, incident_message)
                logger.info(f"Message posted to new channel {channel_id}")
                
                # Posting message to general channel
                general_outages_message = f"🚨New Incident Created in #{channel_name}🚨:\n\n*Description:* {db_incident.start_time} > {db_incident.severity} > {db_incident.affected_products} Outage\n*Severity:* {db_incident.severity}\n*Affected Products:* {', '.join(db_incident.affected_products)}\n*Start Time:* {db_incident.start_time}\n*End Time:* {db_incident.end_time}\n*Customer Affected:* {'Yes' if db_incident.p1_customer_affected else 'No'}\n*Suspected Owning Team:* {db_incident.suspected_owning_team}"
                
                await post_message_to_slack(
                    settings.SLACK_GENERAL_OUTAGES_CHANNEL, general_outages_message
                )
                logger.info(
                    f"Message posted to General Outages Channel: {settings.SLACK_GENERAL_OUTAGES_CHANNEL}"
                )

            

                end_api_calls_time = time.time()
                print(
                    f"Time taken for API calls: {end_api_calls_time - start_api_calls_time} seconds"
                )

            except SlackApiError as slack_error:
                logger.error(
                    f"Slack API error in create_slack_channel: {e.response['error']}"
                )
                logger.error(f"Full Slack error response: {slack_error.response}")

            except Exception as e:
                logger.exception(f"Unexpected error occurred: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"An unexpected error occurred: {str(e)}",
                ) from e

            if db_incident.end_time is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="End time not found"
                )

            db_time = time.time()
            print(
                f"Time to save incident to database: {db_time - start_api_calls_time} seconds"
            )

            return {"incident_id": db_incident.id, "issue_key": issue["key"]}

        return JSONResponse(
            status_code=404, content={"detail": "Command or callback ID not found"}
        )

    return JSONResponse(content={"response_action": "clear"})
