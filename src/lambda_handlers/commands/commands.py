import json
import logging
import os
from fastapi import HTTPException
import httpx
from typing import Dict, Any
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from urllib.parse import parse_qs
from src.utils import verify_slack_request, get_modal_view, create_modal_view, update_modal_view
from config import get_settings, Settings

logger = Logger()


def is_test_mode()-> bool:
    test_mode = os.environ.get('IS_LOCAL_TEST', '').lower() == 'true'
    logger.info(f"Test mode check: {test_mode} (env value: {os.environ.get('IS_LOCAL_TEST')})")
    return test_mode

        
@logger.inject_lambda_context
async def handler(event: Dict[Any, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler for Slack slash commands that display forms
    """
    test_mode = is_test_mode()
    logger.info(f"Handler started in {'test' if test_mode else 'production'} mode")
    
    
    settings = get_settings()
    try:
        # Get and decode body if needed
        body = event['body']
        if isinstance(body, bytes):
            body = body.decode('utf-8')
            
        # Parse form data
        if isinstance(body, str):
            form_data = dict(parse_qs(body))
            form_data = {k: v[0] for k, v in form_data.items()}
        else:
            form_data = body
            
        command = form_data.get("command")
        trigger_id = form_data.get("trigger_id")
        
        if not command or not trigger_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required fields"})
            }
        
        
        # Test mode checks
        logger.info(f"About to check IS_LOCAL_TEST. Value is {command}")
        if test_mode:
            logger.info(f"Test mode: Processing command {command}")

            return {
                'statusCode': 200,
                'body': json.dumps({
                    'response_type': 'ephemeral',
                    'text': f'Form would open for command: {command}'
                })
            }
        
        # Handle verification for non-test mode
        
        headers = event['headers']
        x_slack_signature = headers.get('x-slack-signature')
        x_slack_request_timestamp = headers.get("x-slack-request-timestamp")
            
        # Convert back to bytes for verification
        body_bytes = body.encode('utf-8') if isinstance(body, str) else body
        await verify_slack_request(body_bytes, x_slack_signature, x_slack_request_timestamp, settings)
            
        # Verify token
        token = form_data.get("token")
        if token != settings.SLACK_VERIFICATION_TOKEN:
            return {
                "statusCode": 401,
                "body": json.dumps({"error": "Invalid token"})
            }
        
       
        # Set up Slack headers
        slack_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}",
        }
        
        # Handle different commands
        if command == "/get-incident":
            logger.info("Handling /get-incident command")
            modal_view = await get_modal_view(callback_id="so_lookup_form")
        elif command == "/create-incident":
            logger.info("Handling /create-incident command")
            suggested_so_number = "SO-1234"
            modal_view = await create_modal_view(
                callback_id="incident_form",
                suggested_so_number=suggested_so_number,
            )
        elif command == "/update-incident":
            logger.info("Handling /update-incident command")
            modal_view = await update_modal_view(callback_id="statuspage_update")
        else:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid command"})
            }
            
        # Open modal in Slack
        payload = {"trigger_id": trigger_id, "view": modal_view}
        
        try:
            async with httpx.AsyncClient() as client:
                slack_response = await client.post(
                    "https://slack.com/api/views.open",
                    headers=slack_headers,
                    json=payload,
                    timeout=3
                )
                slack_response.raise_for_status()
                slack_response_data = slack_response.json()
                
                if not slack_response_data.get("ok"):
                    raise HTTPException(
                        status_code=500,
                        detail=slack_response_data.get("error", "Unknown Slack API error")
                    )
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "response_type": "ephemeral",
                        "text": "Form opened successfully"
                    })
                }
        except Exception as e:
            logger.error(f"Error opening Slack modal: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': f"Failed to open form: {str(e)}"})
            }   
            
    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }