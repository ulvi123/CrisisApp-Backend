from fastapi import Request, HTTPException
from .config import settings
import hmac
import hashlib
import json


async def verify_slack_request(
    request: Request, x_slack_signature: str, x_slack_request_timestamp: str
):
    if x_slack_signature is None or x_slack_request_timestamp is None:
        raise HTTPException(
            status_code=400, detail="Missing Slack signature or timestamp"
        )

    body = await request.body()
    sig_base = f"v0:{x_slack_request_timestamp}:{body.decode('utf-8')}"
    my_signature = (
        "v0="
        + hmac.new(
            settings.SLACK_SIGNING_SECRET.encode(), sig_base.encode(), hashlib.sha256
        ).hexdigest()
    )

    if not hmac.compare_digest(my_signature, x_slack_signature):
        raise HTTPException(status_code=400, detail="Invalid request signature")


# async def validate_token(self,cls, values):
#         token = values.get('token')
#         x_slack_signature = values.get('HTTP_X_SLACK_SIGNATURE')
#         slack_request_timestamp = values.get('HTTP_X_SLACK_REQUEST_TIMESTAMP')
#         sig_base = f"v0:{slack_request_timestamp}:{values.get('raw_body')}".encode('utf-8')
#         slack_signing_secret = settings.slack_signing_secret
#         slack_hash = 'v0=' + hmac.new(settings.slack_signing_secret.encode('utf-8'), sig_base, hashlib.sha256).hexdigest()
#         if not hmac.compare_digest(slack_hash, x_slack_signature):
#             raise ValueError("Invalid Slack request signature")
#         return values


async def slack_challenge_parameter_verification(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse JSON body: {str(e)}"
        )
    # Handle URL verification with slack to accept the challenge parameter
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}


async def create_modal_view(callback_id: str) -> dict:
    return {
        "type": "modal",
        "callback_id": callback_id,
        "title": {"type": "plain_text", "text": "Report Incident"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "private_metadata": json.dumps({"callback_id": callback_id}),
        "blocks": [
            {
                "type": "section",
                "block_id": "section1",
                "text": {
                    "type": "mrkdwn",
                    "text": "Please fill out the following incident form:",
                },
            },
            {
                "type": "input",
                "block_id": "affected_products",
                "label": {"type": "plain_text", "text": "Affected Products"},
                "element": {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Select products"},
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Product 1"},
                            "value": "product_1",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Product 2"},
                            "value": "product_2",
                        },
                    ],
                    "action_id": "affected_products_action"
                },
            },
            {
                "type": "input",
                "block_id": "severity",
                "label": {"type": "plain_text", "text": "Severity"},
                "element": {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Select severity"},
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "High"},
                            "value": "high",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Medium"},
                            "value": "medium",
                        },
                        {"text": {"type": "plain_text", "text": "Low"}, "value": "low"},
                    ],
                    "action_id": "severity_action"
                },
            },
            {
                "type": "input",
                "block_id": "suspected_owning_team",
                "label": {"type": "plain_text", "text": "Suspected Owning Team"},
                "element": {
                    "type": "multi_static_select",
                    "placeholder": {"type": "plain_text", "text": "Select teams"},
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Team 1"},
                            "value": "team_1",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Team 2"},
                            "value": "team_2",
                        },
                    ],
                    "action_id": "suspected_owning_team_action"
                },
            },
            {
                "type": "input",
                "block_id": "start_time",
                "element": {
                    "type": "plain_text_input",
                    "placeholder": {"type": "plain_text", "text": "Enter start time"},
                    "action_id": "start_time_action"
                },
                "label": {"type": "plain_text", "text": "Start Time", "emoji": True},
            },
            {
                "type": "input",
                "block_id": "p1_customer_affected",
                "element": {
                    "type": "checkboxes",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "P1 customer affected",
                            },
                            "value": "p1_customer_affected",
                        }
                    ],
                    "action_id": "p1_customer_affected_action"
                },
                "label": {
                    "type": "plain_text",
                    "text": "P1 Customer Affected",
                    "emoji": True,
                },
            },
            {
                "type": "input",
                "block_id": "suspected_affected_components",
                "label": {
                    "type": "plain_text", "text": "Suspected Affected Components",
                },
                "element": {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Select components"},
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Component 1"},
                            "value": "component_1",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Component 2"},
                            "value": "component_2",
                        },
                    ],
                    "action_id": "suspected_affected_components_action"
                },
            },
            {
                "type": "input",
                "block_id": "description",
                "element": {
                    "type": "plain_text_input",
                    "multiline": True,
                    "action_id": "description_action"
                },
                "label": {"type": "plain_text", "text": "Description", "emoji": True},
            },
            {
                "type": "input",
                "block_id": "message_for_sp",
                "element": {
                    "type": "plain_text_input",
                    "multiline": True,
                    "action_id": "message_for_sp_action"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Message for SP",
                    "emoji": True,
                },
                "optional": True,
            },
            {
                "type": "input",
                "block_id": "flags_for_statuspage_notification",
                "element": {
                    "type": "checkboxes",
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Statuspage Notification",
                            },
                            "value": "statuspage_notification",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "Separate Channel Creation",
                            },
                            "value": "separate_channel_creation",
                        },
                    ],
                    "action_id": "flags_for_statuspage_notification_action"
                },
                "label": {"type": "plain_text", "text": "Flags", "emoji": True},
            },
            {
                "type": "actions",
                "block_id": "actionblock789",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Submit"},
                        "value": "click_me_123",
                        "action_id": "button-action",
                    }
                ],
            },
        ],
    }
