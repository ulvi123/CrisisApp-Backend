<<<<<<< HEAD
=======
import os
import json
import time
import hmac
import hashlib
import urllib.parse
import requests
import boto3

from botocore.exceptions import ClientError
from typing import Any, Dict

# Environment variables set via Terraform
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
SLACK_VERIFICATION_TOKEN = os.getenv("SLACK_VERIFICATION_TOKEN", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE_NAME)


def verify_slack_signature(headers: Dict[str, str], raw_body: str) -> None:
    """
    Inline Slack request verification. Raises ValueError on mismatch/expired requests.
    """
    if not SLACK_SIGNING_SECRET:
        raise ValueError("Missing SLACK_SIGNING_SECRET environment variable.")

    slack_signature = headers.get("x-slack-signature")
    slack_timestamp = headers.get("x-slack-request-timestamp")

    if not slack_signature or not slack_timestamp:
        raise ValueError("Missing Slack signature or timestamp headers.")

    # Slack recommends ignoring requests older than 5 minutes to mitigate replay attacks
    now = int(time.time())
    if abs(now - int(slack_timestamp)) > 60 * 5:
        raise ValueError("Slack request timestamp is too old or invalid.")

    sig_basestring = f"v0:{slack_timestamp}:{raw_body}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"),
        sig_basestring.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(my_signature, slack_signature):
        raise ValueError("Invalid Slack signature. Possible forgery.")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda entry point for Slack slash commands, e.g. /create-incident.
    Triggered by an HTTP API Gateway in Terraform.
    """
    # 1) Parse headers & body
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    raw_body = event.get("body", "") or ""

    # 2) Verify Slack signature
    try:
        verify_slack_signature(headers, raw_body)
    except ValueError as e:
        return _error_response(401, str(e))

    # 3) Slash command is form-encoded => parse
    form_data = urllib.parse.parse_qs(raw_body)
    token = form_data.get("token", [""])[0]
    command = form_data.get("command", [""])[0] 
    user_id = form_data.get("user_id", [""])[0]
    channel_id = form_data.get("channel_id", [""])[0]
    text = form_data.get("text", [""])[0]  

    # 4) verify Slack verification token 
    if token != SLACK_VERIFICATION_TOKEN:
        return _error_response(401, "Invalid Slack verification token")

    # 5) Store a minimal record in DynamoDB
    item_id = f"{user_id}-{int(time.time())}"
    try:
        table.put_item(
            Item={
                "IncidentId": item_id,
                "Command": command,
                "Text": text,
                "Environment": ENVIRONMENT,
                "CreatedAt": int(time.time())
            }
        )
    except ClientError as e:
        return _error_response(500, f"DynamoDB error: {str(e)}")

    # 6) If command == "/create-incident", let's open a Slack modal 
    #    using the Slack Bot token and Slack's "views.open" endpoint.
    if command == "/create-incident":
        trigger_id = form_data.get("trigger_id", [""])[0]
        if not trigger_id:
            return _error_response(400, "Missing trigger_id. Slack cannot open a modal without it.")

        # Build a sample modal
        modal_view = {
            "type": "modal",
            "callback_id": "incident_form",
            "title": {"type": "plain_text", "text": "Create Incident"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "description_block",
                    "label": {"type": "plain_text", "text": "Description"},
                    "element": {
                        "type": "plain_text_input",
                        "multiline": True,
                        "action_id": "description_input"
                    }
                }
            ]
        }

        # Post to Slack "views.open"
        slack_api_url = "https://slack.com/api/views.open"
        headers_slack = {
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8"
        }
        payload = {
            "trigger_id": trigger_id,
            "view": modal_view
        }

        resp = requests.post(slack_api_url, headers=headers_slack, data=json.dumps(payload))
        slack_data = resp.json()
        if not slack_data.get("ok"):
            return _error_response(500, f"Error opening modal: {slack_data}")

        # Return ephemeral acknowledgement to Slack
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "response_type": "ephemeral",
                "text": f"Modal opened! DynamoDB ItemId: {item_id}"
            })
        }
    else:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "response_type": "ephemeral",
                "text": f"Received command '{command}' with text '{text}'. ItemId: {item_id}"
            })
        }


def _error_response(status: int, message: str) -> Dict[str, Any]:
    """Helper to format errors for Slack-friendly JSON."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message})
    }
>>>>>>> 3b2ab68 (Lambda codes)
