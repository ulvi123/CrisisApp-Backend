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

# Environment variables
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
SLACK_VERIFICATION_TOKEN = os.getenv("SLACK_VERIFICATION_TOKEN", "")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE_NAME)


def verify_slack_signature(headers: Dict[str, str], raw_body: str) -> None:
    if not SLACK_SIGNING_SECRET:
        raise ValueError("Missing SLACK_SIGNING_SECRET.")

    slack_signature = headers.get("x-slack-signature")
    slack_timestamp = headers.get("x-slack-request-timestamp")

    if not slack_signature or not slack_timestamp:
        raise ValueError("Missing Slack signature or timestamp headers.")

    now = int(time.time())
    if abs(now - int(slack_timestamp)) > 300:  # 5 minutes
        raise ValueError("Request is too old or invalid timestamp.")

    basestring = f"v0:{slack_timestamp}:{raw_body}"
    my_signature = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode("utf-8"),
        basestring.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(my_signature, slack_signature):
        raise ValueError("Invalid Slack signature.")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda for Slack interactive events:
    - Form submissions (view_submission)
    - Button/Block actions
    """
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    raw_body = event.get("body", "") or ""

    # Signature check
    try:
        verify_slack_signature(headers, raw_body)
    except ValueError as e:
        return _error_response(401, str(e))

    # Slack interactive events come in application/x-www-form-urlencoded with "payload"
    form_data = urllib.parse.parse_qs(raw_body)
    payload_str = form_data.get("payload", [""])[0]
    if not payload_str:
        return _error_response(400, "Missing payload in Slack interaction request.")

    # Parse the JSON payload from Slack
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as e:
        return _error_response(400, f"Could not parse JSON: {str(e)}")

    # token check
    token = payload.get("token", "")
    if token != SLACK_VERIFICATION_TOKEN:
        return _error_response(401, "Invalid Slack verification token.")

    user_id = payload.get("user", {}).get("id", "unknown_user")
    view = payload.get("view", {})  # If this is a modal submission
    callback_id = view.get("callback_id", "")
    interaction_type = payload.get("type", "")  # e.g. "view_submission"

    # Incident form submissions
    if interaction_type == "view_submission" and callback_id == "incident_form":
        # Slack modal form data is in `view['state']['values']`, etc.
        state_values = view.get("state", {}).get("values", {})

        # Extracting a "description" from an input block
        description_block = state_values.get("description_block", {})
        desc_action = description_block.get("description_input", {})
        description_text = desc_action.get("value", "No description provided")

        # Store in DynamoDB
        incident_id = f"modal-{user_id}-{int(time.time())}"
        try:
            table.put_item(
                Item={
                    "IncidentId": incident_id,
                    "Description": description_text,
                    "Environment": ENVIRONMENT,
                    "SubmittedBy": user_id,
                    "CreatedAt": int(time.time())
                }
            )
        except ClientError as e:
            return _error_response(500, f"DynamoDB error: {str(e)}")

        # For a view_submission, if everything is good:
        #   "response_action": "clear" => closes the modal
        #   or "response_action": "errors" => display form validation errors
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"response_action": "clear"})
        }

    if interaction_type == "block_actions":
        actions = payload.get("actions", [])


        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "response_action": "update",
                "text": "Block action received!"
            })
        }

    # Default fallback
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"text": "Interaction received, nothing special done."})
    }


def _error_response(status: int, message: str) -> Dict[str, Any]:
    """Helper to return JSON error to Slack."""
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message})
    }
>>>>>>> 3b2ab68 (Lambda codes)
