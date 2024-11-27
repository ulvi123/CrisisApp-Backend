import logging
from fastapi import BackgroundTasks
import requests
import json
from src import models
from src import schemas
from pydantic import ValidationError
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Header, Response, status, Depends
from sqlalchemy.orm import Session
from src.database import get_db
from src.utils import (
    verify_slack_request,
    create_modal_view,
    load_options_from_file,
    get_modal_view,
    update_modal_view
)
from src.helperFunctions.status_page import create_statuspage_incident,update_statuspage_incident_status
from src.helperFunctions.team_channel_mapping_to_slack import get_slack_channel_id_for_team
from src.helperFunctions.generate_next_so_number import generate_next_so_number
from starlette.responses import JSONResponse
from config import get_settings, Settings
from src.helperFunctions.opsgenie import create_alert
from src.helperFunctions.jira import create_jira_ticket
from src.helperFunctions.slack_utils import post_message_to_slack, create_slack_channel,open_slack_response_modal
from urllib.parse import parse_qs
from pydantic import ValidationError
from slack_sdk.errors import SlackApiError
import httpx





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

#Fetching the settings from the configuration file
settings = get_settings()

# Load options at application startup
options = load_options_from_file("options.json")

#create incident slack command
@router.post("/slack/commands")
async def handling_slash_commands(
    request: Request,
    x_slack_request_timestamp: str = Header(None),
    x_slack_signature: str = Header(None),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
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
        suggested_so_number =generate_next_so_number(db)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        }
        modal_view = await create_modal_view(callback_id="incident_form",suggested_so_number=suggested_so_number)
        payload = {"trigger_id": trigger_id, "view": modal_view}
        logger.debug(json.dumps(payload, indent=2,default=str))
        
        try:
            async with httpx.AsyncClient() as client:
                slack_response = await client.post(
                    "https://slack.com/api/views.open",
                    headers=headers,
                    json=payload,
                    timeout=2,
                )
                slack_response.raise_for_status()  # Raise an exception for HTTP errors
                slack_response_data = slack_response.json()  # Parse JSON response

            if not slack_response_data.get("ok"):
                raise HTTPException(
                    status_code=400, detail=f"Slack API error: {slack_response_data}"
                )

            return JSONResponse(
                status_code=200,
                content={
                    "response_type": "ephemeral",
                    "text": "Incident form opening executed successfully in the FastAPI Backend",
                },
            )

        except httpx.RequestError as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to open the form: {str(e)}"
            ) from e
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=400, detail=f"Failed to parse Slack response: {str(e)}"
            ) from e

        # try:
        #     slack_response = requests.post(
        #         "https://slack.com/api/views.open",
        #         headers=headers,
        #         json=payload,
        #         timeout=2,
        #     )
        #     slack_response.raise_for_status()  # Raise an exception for HTTP errors
        #     slack_response_data = slack_response.json()  # Parse JSON response

        # except requests.exceptions.RequestException as e:
        #     raise HTTPException(
        #         status_code=400, detail=f"Failed to open the form: {str(e)}"
        #     ) from e
        # except json.JSONDecodeError as e:
        #     raise HTTPException(
        #         status_code=400, detail=f"Failed to parse Slack response: {str(e)}"
        #     ) from e

        # if not slack_response_data.get("ok"):
        #     raise HTTPException(
        #         status_code=400, detail=f"Slack API error: {slack_response_data}"
        #     )

        # return JSONResponse(
            status_code=200,
            content={
                "response_type": "ephemeral",
                "text": "Incident form opening executed successfully in the fastapi Backend",
            },
        # )

    #slack command to update the incident status in statuspage-logic below
    elif command == "/update-incident":
        logger.info("Handling the incident update command")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        }
        
        modal_view = await update_modal_view(callback_id="statuspage_update")
        payload = {"trigger_id": trigger_id, "view": modal_view}
        logger.debug(json.dumps(payload, indent=2))
        
        try:
            slack_response = requests.post(\
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
                "text": "Incident update form has been opened successfully.",
            },
        )








         
#Route logic to create an incident
@router.post("/slack/interactions", status_code=status.HTTP_201_CREATED,response_model=schemas.IncidentResponse)    
async def slack_interactions(
    request: Request,
    response:Response,
    db: Session = Depends(get_db),
    x_slack_signature: str = Header(None),
    x_slack_request_timestamp: str = Header(None),
    settings: Settings = Depends(get_settings),
):
    body = await request.body()
    await verify_slack_request(
        body, x_slack_signature, x_slack_request_timestamp, settings
    )

    decoded_body = parse_qs(body.decode("utf-8"))
    payload_str = decoded_body.get("payload", [None])[0]
    if not payload_str:
        logging.error("Missing payload in the request")
        raise HTTPException(status_code=400, detail="Missing payload")
    # Parsing the payload here
    try:
        payload = json.loads(payload_str)
        print(f"Payload: {json.dumps(payload, indent=2)}")
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse request body: {str(e)}"
        ) from e
        
    
    
    # Verifying the signature
    token = payload.get("token")
    if token != settings.SLACK_VERIFICATION_TOKEN:
        logging.error("Invalid Slack verification token")
        raise HTTPException(status_code=400, detail="Invalid token")
        
    
    #Extracting user id for usage in sending slack messages
    user_id = payload.get("user",{}).get("id")
    if not user_id:
        logging.error("Missing user_id in the payload")
        raise HTTPException(status_code=400, detail="Missing user_id")
    
    #Extracting trigger id
    trigger_id = payload.get("trigger_id")
    if not trigger_id:
        logging.error("Missing trigger_id in the payload")
        raise HTTPException(status_code=400, detail="Missing trigger_id")
    
    
    #Fetching the callback id to differentiate between 2 slack events
    callback_id = payload.get("view",{}).get("callback_id")
    
    # Processing the actual interaction based on the propagated event
    if payload.get("type") == "view_submission": 
        #Alternative verison for optimized response
        if callback_id == "incident_form":
            background_tasks = BackgroundTasks()
            try:
                state_values = payload.get("view",{}).get("state", {}).get("values", {})
                logger.debug("State values: %s", json.dumps(state_values, indent=2))
                
                incident_data = extract_incident_data(state_values)
                
                background_tasks.add_task(
                    process_incident_creation,
                    incident_data,
                    trigger_id,
                    settings,
                    db 
                )
                
                #Retruning here immediate response to slack
                return JSONResponse(
                    status_code=200,
                    content={
                        "response_action":"clear",
                    },
                    background=background_tasks
                )
            except ValidationError as e:
                    return JSONResponse(
                        status_code=200,
                        content={
                            "response_action": "errors",
                            "errors": {"incident_form": str(e)}
                        }
                    )
            except Exception as e:
                        logger.error("Error in form processing: %s", str(e), exc_info=True)
                        return JSONResponse(
                            status_code=200,
                            content={
                                "response_action": "errors",
                                "errors": {"incident_form": str(e)}
                            }
                        )        

        #Handling the fetching of incident from the SLACK form
        elif callback_id == "so_lookup_form" :
            try:
                state_values = payload.get("view",{}).get("state",{}).get("values",{})
                so_number = state_values.get("so_number")
                if not so_number:
                    logging.error("Missing 'so_number_block' in the Slack payload.")
                    raise HTTPException(status_code=400, detail="SO Number block missing in form submission.")

                so_number_action = so_number.get("so_number_action")
                if not so_number_action:
                    logging.error("Missing 'so_number_action' in the Slack payload.")
                    raise HTTPException(status_code=400, detail="SO Number action missing in form submission.")

                # Now, safely getting  the 'value' here
                so_number = so_number_action.get("value")
                if not so_number:
                    logging.error("SO Number is missing in the Slack form submission.")
                    raise HTTPException(
                        status_code=400, detail="SO Number is required but missing from the form submission."
                    )

                    
                #fetching the incident from the database
                db_incident = db.query(models.Incident).filter(models.Incident.so_number == so_number).first()
                
                if not db_incident:
                    return JSONResponse(
                        status_code=200,
                        content={
                            "response_action": "update",
                            "view": {
                                "type": "modal",
                                "title": {"type": "plain_text", "text": "SO Lookup"},
                                "close": {"type": "plain_text", "text": "Close"},
                                "blocks": [
                                    {
                                        "type": "section",
                                        "text": {
                                            "type": "mrkdwn",
                                            "text": f"No incident found for SO Number: *{so_number}*."
                                        }
                                    }
                                ]
                            }
                        }
                    )
                
                #Constructing jira URL by using the incident's jira issue key
                jira_issue_key = db_incident.jira_issue_key
                if not jira_issue_key:
                    raise HTTPException(status_code=400, detail="Jira issue key is missing in the database.")
                
                jira_link = f"{settings.jira_server}/browse/{jira_issue_key}"
    
            
                #Sending the message to the user
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
                }
                
                incident_message = (
                    f"🚨 *Incident Details* 🚨:\n\n"
                    f"*SO Number:* {db_incident.so_number}\n"
                    f"*Severity:* {', '.join(db_incident.severity) if db_incident.severity else 'None'}\n"
                    f"*Affected Products:* {', '.join(db_incident.affected_products)}\n"
                    f"*Suspected Owning Team:* {', '.join(db_incident.suspected_owning_team)}\n"
                    f"*Start Time:* {db_incident.start_time}\n"
                    f"*End Time:* {db_incident.end_time}\n"
                    f"*Customer Affected:* {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
                    f"*Description:* {db_incident.description}\n"
                    f"*Jira Link:* {jira_link}\n"
                )
                
                response_payload = {
                    "channel":user_id,
                    "text":incident_message,
                    "as_user":True
                }

                try:
                    response = requests.post(
                        "https://slack.com/api/chat.postMessage", headers=headers, json=response_payload, timeout=10)
                    data = response.json()
                    if response.status_code != 200 or not data.get("ok"):
                        print(f"Error sending Slack message: {data}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"An unexpected error occurred: {data['error']}",
                        )
                except requests.RequestException as e:
                    print(f"Error sending Slack message: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"An unexpected error occurred",
                    )
            
                return JSONResponse(status_code=200,content={
                    "response_action":"clear"
                })
            

            except KeyError as e:
                print(f"Error retrieving state values: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="State values not found in the view payload",
                )
            
        #Handling the updating of incident in the statuspage
        elif callback_id == "statuspage_update":
            state_values = payload.get("view",{}).get("state",{}).get("values",{})
            #Extracting values from the slack payload
            so_number = state_values.get("so_number", {}).get("so_number_action", {}).get("value")
            if not so_number:
                logging.error("Missing 'SO_number_block' in the Slack payload.")
                raise HTTPException(status_code=400, detail="SO Number is required.")
            new_status = state_values.get("status_update_block", {}).get("status_action", {}).get("selected_option", {}).get("value")
            additional_info = state_values.get("additional_info_block", {}).get("additional_info_action", {}).get("value", "")
            
            #Introducing the validations section
            if not so_number and not new_status:
                raise HTTPException(status_code=400, detail="SO Number and new status are required.")
            
            #Fetching the incident from the database
            db_incident = db.query(models.Incident).filter(models.Incident.so_number == so_number).first()
            if not db_incident:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No incident found with SO Number: {so_number}"
                )
            
            # Creating a background task to update the Statuspage incident status
            background_tasks = BackgroundTasks()
            background_tasks.add_task(
                update_statuspage_incident_status,
                db_incident=db_incident,
                new_status=new_status,
                additional_info=additional_info,
                settings=settings
            )
            
            # Return an immediate response to the Slack user
            return JSONResponse(
                status_code=200,
                content={
                    "response_type": "ephemeral",
                    "view": {
                        "type": "modal",
                        "title": {"type": "plain_text", "text": "Status Update"},
                        "close": {"type": "plain_text", "text": "Close"},
                        "blocks": [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"Status of SO Number: *{so_number}* is being updated to *{new_status}*."
                                }
                            }
                        ]
                    }
                },
                background=background_tasks
    )
        
    return JSONResponse(status_code=response.status_code,content={
        "response":'success'
    })



def extract_incident_data(state_values):
    required_fields = ["start_time", "start_time_picker", "end_time", "end_time_picker", "so_number", "affected_products", "suspected_owning_team", "severity"]
    
    for field in required_fields:
        if field not in state_values:
            logger.error(f"Missing {field} in state values")
            raise ValueError(f"Missing {field}")
    
    start_date = state_values.get("start_time", {}).get("start_date_action", {}).get("selected_date")
    start_time = state_values.get("start_time_picker", {}).get("start_time_picker_action", {}).get("selected_time")
    end_date = state_values.get("end_time", {}).get("end_date_action", {}).get("selected_date")
    end_time = state_values.get("end_time_picker", {}).get("end_time_picker_action", {}).get("selected_time")

    if not start_date or not start_time:
        raise ValueError("Missing start datetime")
    if not end_date or not end_time:
        raise ValueError("Missing end datetime")

    start_datetime_str = f"{start_date}T{start_time}:00"
    end_datetime_str = f"{end_date}T{end_time}:00"

    try:
        start_time_obj = datetime.strptime(start_datetime_str, "%Y-%m-%dT%H:%M:%S")
        end_time_obj = datetime.strptime(end_datetime_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError as e:
        raise ValueError("Invalid datetime format") from e

    so_number = state_values.get("so_number", {}).get("so_number_action", {}).get("value")
    if not so_number:
        logger.error("Missing SO number")
        raise ValueError("Missing SO number")

    affected_products_options = state_values.get("affected_products", {}).get("affected_products_action", {}).get("selected_options", [])
    affected_products = [option["value"] for option in affected_products_options]

    suspected_owning_team_options = state_values.get("suspected_owning_team", {}).get("suspected_owning_team_action", {}).get("selected_options", [])
    suspected_owning_team = [option["value"] for option in suspected_owning_team_options]

    suspected_affected_components_options = state_values.get("suspected_affected_components", {}).get("suspected_affected_components_action", {}).get("selected_options", [])
    suspected_affected_components = [option["value"] for option in suspected_affected_components_options]

    severity_option = state_values.get("severity", {}).get("severity_action", {}).get("selected_option", {})
    severity = severity_option.get("value") if severity_option else None
    severity = [severity] if severity else []

    return {
        "so_number": so_number,
        "affected_products": affected_products,
        "severity": severity,
        "suspected_owning_team": suspected_owning_team,
        "start_time": start_time_obj.isoformat(),
        "end_time": end_time_obj.isoformat(),
        "p1_customer_affected": extract_checkbox(state_values, "p1_customer_affected"),
        "suspected_affected_components": suspected_affected_components,
        "description": state_values.get("description", {}).get("description_action", {}).get("value"),
        "message_for_sp": state_values.get("message_for_sp", {}).get("message_for_sp_action", {}).get("value", ""),
        "statuspage_notification": extract_checkbox(state_values, "flags_for_statuspage_notification", "statuspage_notification"),
        "separate_channel_creation": extract_checkbox(state_values, "flags_for_statuspage_notification", "separate_channel_creation"),
    }

def extract_checkbox(state_values, key, value=None):
    options = state_values.get(key, {}).get(f"{key}_action", {}).get("selected_options", [])
    return any(option.get("value") == (value or key) for option in options)
    
async def process_incident_creation(incident_data: dict, trigger_id: str, settings: Settings, db: Session):
    logger.info("Starting incident creation process")
    try:
        
        # Create Jira ticket
        incident = schemas.IncidentCreate(**incident_data)
        issue = await create_jira_ticket(incident)
        
        # Update incident data
        incident_data["so_number"] = issue["key"]
        incident_data["jira_issue_key"] = issue["key"]
        
        # Save to database
        db_incident = models.Incident(**incident_data)
        try:
            db.add(db_incident)
            db.commit()
            db.refresh(db_incident)
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            db.rollback()
            raise

        # Send success message to Slack
        try:
            await open_slack_response_modal(
                trigger_id=trigger_id,
                modal_type="success",
                incident_data={
                    "so_number": incident_data["so_number"],
                    "severity": incident_data["severity"],
                    "jira_url": f"{settings.jira_server}/browse/{issue['key']}"
                }
            )
        except Exception as slack_error:
            logger.error(f"Error sending Slack success message: {str(slack_error)}")
            await open_slack_response_modal(
                trigger_id=trigger_id,
                modal_type="error",
                incident_data={
                    "error": str(slack_error)
                }
            )

        # Create Slack channels and send messages
        try:
            channel_name = f"incident-{db_incident.so_number}".lower()
            channel_id = await create_slack_channel(channel_name)
            incident_message = create_incident_message(db_incident, settings)
            await post_message_to_slack(channel_id, incident_message)
            logger.info(f"Posted message to incident channel {channel_name}")
            
            # Post to general outages channel
            general_outages_message = create_general_outages_message(db_incident, channel_id)
            await post_message_to_slack(settings.SLACK_GENERAL_OUTAGES_CHANNEL, general_outages_message)
            logger.info("Posted message to general outages channel")
            
            # Post to team channel
            if db_incident.suspected_owning_team:
                team_name = db_incident.suspected_owning_team[0]
                team_channel_id = get_slack_channel_id_for_team(team_name)
                if team_channel_id:
                    team_message = create_team_message(db_incident, channel_id)
                    await post_message_to_slack(team_channel_id, team_message)
                    logger.info(f"Posted message to {team_name} team channel")

        except Exception as slack_error:
            logger.error(f"Slack API error: {str(slack_error)}")
            
        # Handle Statuspage
        if db_incident.statuspage_notification:
            try:
                statuspage_response = await create_statuspage_incident(db_incident, settings, db)
                logger.info(f"Statuspage incident created with ID: {statuspage_response.get('id')}")
                db_incident.statuspage_incident_id = statuspage_response.statuspage_incident_id
                db.commit()
            except Exception as e:
                logger.error(f"Unexpected error creating Statuspage incident for SO {db_incident.so_number}: {str(e)}")
                db_incident.status = "STATUSPAGE_CREATION_FAILED"
                db.commit()

        #Create OpsGenie alert
        try:
            opsgenie_response = await create_alert(db_incident)
            if opsgenie_response["status_code"] == 201:
                logger.info(f"OpsGenie alert created with ID: {opsgenie_response.json()['id']}")
            else:
                logger.error("Failed to create OpsGenie alert")
        except Exception as e:
            logger.error(f"Error creating OpsGenie alert: {str(e)}")

    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}", exc_info=True)
        try:
            await open_slack_response_modal(
                trigger_id=trigger_id,
                modal_type="error",
                incident_data={
                    "error": "An unexpected error occurred during incident creation. Please try again or contact support."
                }
            )
        except Exception as slack_error:
            logger.error(f"Error sending Slack error message: {str(slack_error)}")

    logger.info("Incident creation process completed")

def create_incident_message(db_incident, settings):
    return (
        f"\U0001F6A8 *New Incident Created* \U0001F6A8\n\n"
        f"*Incident Summary:*\n"
        f"----------------------------------\n"
        f"*SO Number:* {db_incident.so_number}\n"
        f"*Severity Level:* {', '.join(db_incident.severity)}\n"
        f"*Affected Products:* {', '.join(db_incident.affected_products)}\n"
        f"*Customer Impact:* {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
        f"*Suspected Owning Team:* {', '.join(db_incident.suspected_owning_team)}\n"
        f"\n"
        f"*Time Details:*\n"
        f"----------------------------------\n"
        f"Start Time: {db_incident.start_time}\n"
        f"\n"
        f"*Additional Information:*\n"
        f"----------------------------------\n"
        f"🔗 *Jira Link:* [View Incident in Jira]({settings.jira_server}/browse/{db_incident.jira_issue_key})"
    )

def create_general_outages_message(db_incident, channel_id):
    return (
        f"\U0001F6A8 *New Incident Created* \U0001F6A8\n\n"
        f"Incident Summary\n"
        f"------------------------\n"
        f"SO Number: {db_incident.so_number}\n"
        f"Severity: {', '.join(db_incident.severity)}\n"
        f"Affected Products: {', '.join(db_incident.affected_products)}\n"
        f"Customer Impact: {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
        f"Suspected Owning Team: {', '.join(db_incident.suspected_owning_team)}\n\n"
        f"*Time Details:*\n"
        f"------------------------\n"
        f"Start Time: {db_incident.start_time}\n"
        f"*Additional Information:*\n"
        f"----------------------------------\n"
        f"Join the discussion in the newly created incident channel: <#{channel_id}>"
    )

def create_team_message(db_incident, channel_id):
    return (
        f"\U0001F6A8 *New Incident Created* \U0001F6A8\n\n"
        f"Incident Summary\n"
        f"------------------------\n"
        f"SO Number: {db_incident.so_number}\n"
        f"Severity: {', '.join(db_incident.severity)}\n"
        f"Affected Products: {', '.join(db_incident.affected_products)}\n"
        f"Customer Impact: {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
        f"Suspected Owning Team: {', '.join(db_incident.suspected_owning_team)}\n\n"
        f"*Time Details:*\n"
        f"------------------------\n"
        f"Start Time: {db_incident.start_time}\n"
        f"*Additional Information:*\n"
        f"----------------------------------\n"
        f"Join the discussion in the newly created incident channel: <#{channel_id}>"
    )



