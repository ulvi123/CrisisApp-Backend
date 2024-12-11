import json
import logging
import os
from typing import Dict,Any
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from urllib.parse import parse_qs
from config import get_settings
from src.utils import verify_slack_request
from .form_handlers import handle_incident_form,handle_lookup_form,handle_statuspage_update


logger = Logger()

def is_test_mode() ->bool:
    test_mode = os.environ.get("IS_LOCAL_TEST","").lower() == "true"
    logger.info(f"Test mode check:{test_mode}")
    return test_mode


@logger.inject_lambda_context
async def handler(event:Dict[Any,Any],context:LambdaContext) ->Dict[str,Any]:
    """
    Lambda handler for slack interactions(slack modal/form submisisons)
    
    """
    test_mode = is_test_mode()
    logger.info(f"Handler started in {'test' if test_mode else 'production'} mode")
    settings = get_settings()
    
    try:
        body=event['body']
        if isinstance(body,bytes):
            body = body.decode('utf-8')
            
        # Skip verification in test mode but continue with form processing
        if not test_mode:
            headers = event['headers']
            x_slack_signature = headers.get('x-slack-signature')
            x_slack_request_timestamp = headers.get('x-slack-request-timestamp')
            body_bytes = body.encode('utf-8') if isinstance(body, str) else body
            await verify_slack_request(body_bytes, x_slack_signature, x_slack_request_timestamp, settings)
            
         #Parsing payload
        decoded_body = parse_qs(body)
        payload_str = decoded_body.get("payload",[None])[0]
        
        if not payload_str:
            return {
                "statusCode":400,
                "body":json.dumps({"error":"Missing payload"})
            }

        #Now parsing the json payload
        try:
            payload = json.loads(payload_str)
            logger.debug(f"Parsed payload: {json.dumps(payload, indent=2)}")
        except json.JSONDecodeError as e:
            return {
                "statusCode":400,
                "body":json.dumps({"error":f"Failed to parse payload: {str(e)}"})
            }
            
        #Validating the token
        token = payload.get("token")
        if not test_mode and token != settings.SLACK_VERIFICATION_TOKEN:
            return {
                "statusCode":401,
                "body":json.dumps({"error":"Invalid token"})
            }
            
        #Extracting common fields
        
        user_id = payload.get("user",{}).get("id")
        trigger_id = payload.get("trigger_id")
        callback_id = payload.get("view",{}).get("callback_id")
        
        
        #Routing to the related handler based on interaction type
        if payload.get("type") == "view_submission":
            if callback_id == "incident_form":
                return await handle_incident_form(payload,settings)
            elif callback_id == "so_lookup_form" :
                return await handle_lookup_form(payload,settings)
            elif callback_id == "statuspage_update":
                return await handle_statuspage_update(payload,settings)
            else:
                return {
                    "statusCode":400,
                    "body":json.dumps({"error":f"Unknown callback_id: {callback_id}"})
                }
        
        return {
            "statusCode":200,
            "body":json.dumps({"response":"success"})
        }
    
    except Exception as e:
        logger.error(f"Error processing interaction: {str(e)}")
        return {
            "statusCode":500,
            "body":json.dumps({"error": str(e)})
        }
    
