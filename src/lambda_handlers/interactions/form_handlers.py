import json
import logging
from typing import Dict,Any
from aws_lambda_powertools import Logger
from pydantic import ValidationError
from src.helperFunctions.jira import create_jira_ticket
from src.helperFunctions.slack_utils import (
    open_slack_response_modal, 
    create_slack_channel, 
    post_message_to_slack
)
from src.helperFunctions.opsgenie import create_alert
from src.helperFunctions.status_page import create_statuspage_incident,update_statuspage_incident_status
from .helpers import process_incident_creation
from .helpers import extract_incident_data
import httpx



logger = Logger()

async def handle_incident_form(payload:Dict[str,Any],settings:dict,db: None = None)-> Dict[str, Any]:
    try:
       logger.info("Received incident form payload")
       state_values = payload.get("view", {}).get("state", {}).get("values", {})
       logger.debug("State values received: %s", json.dumps(state_values, indent=2))

        # Log before extraction
       logger.info("Attempting to extract incident data")
       incident_data = extract_incident_data(state_values)
       logger.info(f"Successfully extracted incident data: {json.dumps(incident_data, indent=2)}")
       
       
       required_fields = ["so_number", "severity", "affected_products", "start_time"]
       for field in required_fields:
            if field not in incident_data:
                logger.error(f"Missing required field: {field}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'response_action': 'errors',
                        'errors': {f'Missing required field: {field}'}
                    })
                }
          

       
        # Log before processing
       logger.info("Starting incident creation process")
       if db:
            logger.info("Database provided, processing with DB")
            await process_incident_creation(incident_data, payload.get("trigger_id"), settings, db)
       else:
            logger.info("No database provided, processing without DB")
            await process_incident_creation(incident_data, payload.get("trigger_id"), settings)

       return {
            "statusCode": 200,
            "body": json.dumps({"response_action": "clear"})
        }
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "response_action": "errors",
                "errors": {'incident_form': str(e)}
            })
        }
    except Exception as e:
        logger.error("Error in form processing: %s", str(e), exc_info=True)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'response_action': 'errors',
                'errors': {'incident_form': str(e)}
            })
        }

async def handle_lookup_form(payload: Dict[str, Any], settings: dict, db: None = None) -> Dict[str, Any]:
    try:
        logger.info("Received lookup form payload")
        state_values = payload.get("view", {}).get("state", {}).get("values", {})
        logger.debug("State values: %s", json.dumps(state_values, indent=2))

        # Extract SO number with your exact validation
        so_number = state_values.get("so_number")
        if not so_number:
            logger.error("Missing 'so_number_block' in the Slack payload.")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'response_action': 'errors',
                    'errors': {'so_number': 'SO Number block missing in form submission'}
                })
            }

        so_number_action = so_number.get("so_number_action")
        if not so_number_action:
            logger.error("Missing 'so_number_action' in the Slack payload.")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'response_action': 'errors',
                    'errors': {'so_number': 'SO Number action missing in form submission'}
                })
            }

        so_number = so_number_action.get("value")
        if not so_number:
            logger.error("SO Number is missing in the Slack form submission.")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'response_action': 'errors',
                    'errors': {'so_number': 'SO Number is required but missing from the form submission'}
                })
            }

        # Handling here no database case for testing
        if not db:
            logger.info("No database provided, returning test response")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'response_action': 'update',
                    'view': {
                        'type': 'modal',
                        'title': {'type': 'plain_text', 'text': 'SO Lookup'},
                        'close': {'type': 'plain_text', 'text': 'Close'},
                        'blocks': [
                            {
                                'type': 'section',
                                'text': {
                                    'type': 'mrkdwn',
                                    'text': f"Test mode: Would look up SO Number: *{so_number}*"
                                }
                            }
                        ]
                    }
                })
            }

        # Fetch incident from database
        db_incident = db.query(models.Incident).filter(models.Incident.so_number == so_number).first()
        
        if not db_incident:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'response_action': 'update',
                    'view': {
                        'type': 'modal',
                        'title': {'type': 'plain_text', 'text': 'SO Lookup'},
                        'close': {'type': 'plain_text', 'text': 'Close'},
                        'blocks': [
                            {
                                'type': 'section',
                                'text': {
                                    'type': 'mrkdwn',
                                    'text': f"No incident found for SO Number: *{so_number}*."
                                }
                            }
                        ]
                    }
                })
            }

        # Get Jira link
        jira_issue_key = db_incident.jira_issue_key
        if not jira_issue_key:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'response_action': 'errors',
                    'errors': {'jira': 'Jira issue key is missing in the database'}
                })
            }
        
        jira_link = f"{settings.jira_server}/browse/{jira_issue_key}"

        # Prepare message
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

        # Send message to Slack
        user_id = payload.get("user", {}).get("id")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        }
        
        response_payload = {
            "channel": user_id,
            "text": incident_message,
            "as_user": True
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers=headers,
                    json=response_payload,
                    timeout=10
                )
                data = response.json()
                
                if not data.get("ok"):
                    logger.error(f"Error sending Slack message: {data}")
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'response_action': 'errors',
                            'errors': {'slack': f'Failed to send message: {data.get("error")}'}
                        })
                    }
        except Exception as e:
            logger.error(f"Error sending Slack message: {str(e)}")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'response_action': 'errors',
                    'errors': {'slack': 'Failed to send message'}
                })
            }

        return {
            'statusCode': 200,
            'body': json.dumps({
                'response_action': 'clear'
            })
        }

    except KeyError as e:
        logger.error(f"Error retrieving state values: {str(e)}")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'response_action': 'errors',
                'errors': {'form': 'State values not found in the view payload'}
            })
        }
    except Exception as e:
        logger.error(f"Error in lookup form processing: {str(e)}", exc_info=True)
        return {
            'statusCode': 200,
            'body': json.dumps({
                'response_action': 'errors',
                'errors': {'form': str(e)}
            })
        }
               
async def handle_statuspage_update(payload:Dict[str,Any],settings:dict,db:None=None):
    
    try:
       logger.info("Updating the status of the incident")
       state_values = payload.get("view",{}).get("state",{}).get("values",{})
       logger.debug("State Values: %s",json.dumps(state_values,indent=2))
    
       # Extracting values from the slack payload
       so_number = state_values.get("so_number", {}).get("so_number_action", {}).get("value")
       new_status = state_values.get("status_update_block", {}).get("status_action", {}).get("selected_option", {}).get("value")
       additional_info = state_values.get("additional_info_block", {}).get("additional_info_action", {}).get("value", "")
       
       logging.info(f"Received values - SO Number: {so_number}, New Status: {new_status}, Additional Info: {additional_info}")

       if not new_status or not additional_info:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "response_action": "errors",
                    "errors": {"statuspage_update_form": "Status and additional information are required."}
                })
            }
        
       if not so_number:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "response_action": "errors",
                    "errors": {"statuspage_update_form": "SO Number is required."}
                })
            }
                
       if not db:
            logger.info("No database provided")
            return {
                'statusCode': 200,
                'body': json.dumps({
                'response_action': 'errors',
                    'errors': {'database': 'No database connection found'}
                })
            }
        
       db_incident = db.query(models.Incident).filter(models.Incident.so_number == so_number).first()
       if not db_incident:
            return {
                'statusCode': 200,
                'body': json.dumps({
                'response_action': 'errors',
                    'errors': {'so_number': 'No incident found in the database'}
                })
            }
        
       update_result = await update_statuspage_incident_status(
            db_incident = db_incident,
            new_status = new_status,
            additional_info = additional_info,
            settings = settings
        )
    
        # Return a response to the Slack user
       if update_result.get("status") == "success":
            return {
                "statusCode":200,
                "body":json.dumps({
                "response_action": "update",
                        "view": {
                            "type": "modal",
                            "title": {"type": "plain_text", "text": "Status Update"},
                            "close": {"type": "plain_text", "text": "Close"},
                            "blocks": [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"Status of SO Number: *{so_number}* has been successfully updated to *{new_status}*."
                                    }
                                }
                            ]
                    } 
                })
            }
    
       else:
            error_message = update_result.get("message","Unknown error occurred during status update")
            return {
                "statusCode":400,
                "body": json.dumps({
                        "response_action": "errors",
                        "errors": {"statuspage_update_form": error_message}
                    })
            }
    
    
    except Exception as e:
        logging.error(f"Error in statuspage update form processing: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "response_action": "errors",
                "errors": {"statuspage_update_form": str(e)}
            })
        }