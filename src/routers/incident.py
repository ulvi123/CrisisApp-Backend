import asyncio
import logging
from fastapi import APIRouter, Request, HTTPException, Header, status, Depends
import httpx
from sqlalchemy.orm import Session
from src import models
from src import schemas
from src.database import get_db
from src.utils import (
    verify_slack_request,
    create_modal_view,
    load_options_from_file,
    get_modal_view,
    get_incident_details_modal
)
from src.helperFunctions.status_page import create_statuspage_incident
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
import json


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
        # Handling the incident form creation submission
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
                so_number = (state_values.get("so_number", {}).get("so_number_action", {}).get("value"))
                
                #checking if so number is properly extracted from slack payload
                if not so_number:
                    logger.error("Missing SO number")
                    print("Missing SO number")
                else:
                    print(f"SO number: {so_number}")
                
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
                
                
            
                # Creating the incident data
                incident_data = {
                    "so_number": so_number,
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
                    
                }

            except ValidationError as e:
                raise HTTPException(
                    status_code=400, detail=f"Failed to parse request body: {str(e)}"
                ) from e


            

            #Creating jira first
            incident = schemas.IncidentCreate(**incident_data)
            issue = await create_jira_ticket(incident)
            
            #Updating the incident with correct SO number
            incident_data["so_number"] = issue["key"]
            
            #Saving to the database
            db_incident = models.Incident(**incident_data)
            db.add(db_incident)
            db.commit()
            db.refresh(db_incident)
            
        
            #Sending the incident to Statuspage
            try:
                incident_data = db_incident.__dict__  if isinstance (db_incident,models.Incident) else db_incident
                await create_statuspage_incident(incident_data,settings)
                logger.info(f"Statuspage incident created with ID: {db_incident.id}")
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
                )
                
         
            # Slack channel creation integration here
            try:
                start_api_calls_time = time.time()
                channel_name = f"incident-{db_incident.suspected_owning_team[0].replace( ' ', '-' ).lower()}"
                channel_id = await create_slack_channel(channel_name)
                incident_message = (
                    f"🚨 *New Incident Created* 🚨:\n\n"
                    f"*SO Number:* {db_incident.so_number}\n"
                    f"*Description:* {db_incident.start_time} > {db_incident.severity} > {db_incident.affected_products} Outage\n"
                    f"*Severity:* {db_incident.severity}\n"
                    f"*Affected Products:* {', '.join(db_incident.affected_products)}\n"
                    f"*Start Time:* {db_incident.start_time}\n"
                    f"*End Time:* {db_incident.end_time}\n"
                    f"*Customer Affected:* {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
                    f"*Suspected Owning Team:* {', '.join(db_incident.suspected_owning_team)}"
                    f"*Jira Link:* {settings.jira_server}/browse/{db_incident.jira_issue_key}"
                )
                
                await post_message_to_slack(channel_id, incident_message)
                
                
                # Posting message to general channel
                general_outages_message = f"🚨New Incident Created in #{channel_name}🚨:\n\n*Description:* {db_incident.start_time} > {db_incident.severity} >{db_incident.so_number}> {db_incident.affected_products} Outage\n*Severity:* {db_incident.severity}\n*Affected Products:* {', '.join(db_incident.affected_products)}\n*Start Time:* {db_incident.start_time}\n*End Time:* {db_incident.end_time}\n*Customer Affected:* {'Yes' if db_incident.p1_customer_affected else 'No'}\n*Suspected Owning Team:* {db_incident.suspected_owning_team}\n"
                
                await post_message_to_slack(
                    settings.SLACK_GENERAL_OUTAGES_CHANNEL, general_outages_message
                )
               
                end_api_calls_time = time.time()
                print(
                    f"Time taken for API calls: {end_api_calls_time - start_api_calls_time} seconds"
                )

            except SlackApiError as slack_error:
                print(f"Slack API error in create_slack_channel: {slack_error.response['error']}")
                
            
            
          
                

            except Exception as e:
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
                    response_data = response.json()
                    if response.status_code != 200 or not response_data.get("ok"):
                        print(f"Error sending Slack message: {response_data}")
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"An unexpected error occurred: {response_data['error']}",
                        )
                except requests.RequestException as e:
                    print(f"Error sending Slack message: {str(e)}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"An unexpected error occurred",
                    )
            
        
            

            except KeyError as e:
                print(f"Error retrieving state values: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="State values not found in the view payload",
                )

    
    # return JSONResponse(status_code=response.status_code, content=response_data)
