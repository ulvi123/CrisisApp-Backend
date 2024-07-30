import os
import json
from fastapi import HTTPException, status,Request
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.config import settings
import hmac
import hashlib
import time

slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)

async def load_options_from_file(file_path: str) -> dict:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} does not exist.")
    
    with open(file_path, "r") as f:
        options = json.load(f)
    
    return options

async def verify_slack_request(
    request: Request, x_slack_signature: str, x_slack_request_timestamp: str
):
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

async def post_message_to_slack(channel_id: str, message: str):
    try:
        slack_client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        print(f"Message posted to Slack channel ID {channel_id}")
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}")  # Logging the error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Slack API error: {e.response['error']}")

async def create_slack_channel(channel_name: str) -> str:
    try:
        response = slack_client.conversations_create(
            name=channel_name,
            is_private=True  # True if you want a private channel
        )
        channel_id = response["channel"]["id"]
        print(f"Channel created successfully. Channel ID: {channel_id}")
        return channel_id
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Slack API error: {e.response['error']}")

async def get_channel_id(channel_name: str) -> str:
        try:
            response = slack_client.conversations_list()
            for channel in response['channels']:
                if channel['name'] == channel_name:
                    print(f"Channel already exists. Channel ID: {channel['id']}")
                    return channel['id']
            return None
        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Slack API error: {e.response['error']}")
        time.sleep(1)
        attempt += 1

async def create_modal_view(callback_id: str, options: dict) -> dict:
    return {
        "type": "modal",
    "callback_id": "incident_form",
    "title": {"type": "plain_text", "text": "Report Incident"},
    "submit": {"type": "plain_text", "text": "Submit"},
    "close": {"type": "plain_text", "text": "Cancel"},
    "blocks": [
        {
            "type": "section",
            "block_id": "section1",
            "text": {
                "type": "mrkdwn",
                "text": "Please fill out the following incident form:"
            }
        },
        {
            "type": "input",
            "block_id": "affected_products",
            "label": {
                "type": "plain_text",
                "text": "Affected Products"
            },
            "element": {
                "type": "multi_static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select products"
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "BetBuilder"
                        },
                        "value": "BetBuilder"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "BetVision"
                        },
                        "value": "BetVision"
                    }
                ],
                "action_id": "affected_products_action"
            }
        },
        {
            "type": "input",
            "block_id": "severity",
            "label": {
                "type": "plain_text",
                "text": "Severity"
            },
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select severity"
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "High"
                        },
                        "value": "high"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Medium"
                        },
                        "value": "medium"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Low"
                        },
                        "value": "low"
                    }
                ],
                "action_id": "severity_action"
            }
        },
        {
            "type": "input",
            "block_id": "suspected_owning_team",
            "label": {
                "type": "plain_text",
                "text": "Suspected Owning Team"
            },
            "element": {
                "type": "multi_static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select teams"
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Fixtures"
                        },
                        "value": "Fixtures"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Sportsbook Management Integrations"
                        },
                        "value": "Sportsbook Management Integrations"
                    }
                ],
                "action_id": "suspected_owning_team_action"
            }
        },
        {
            "type": "input",
            "block_id": "start_time",
            "label": {
                "type": "plain_text",
                "text": "Start Time",
                "emoji": True
            },
            "element": {
                "type": "datepicker",
                "action_id": "start_date_action"
            }
        },
        {
            "type": "input",
            "block_id": "end_time",
            "label": {
                "type": "plain_text",
                "text": "End Time",
                "emoji": True
            },
            "element": {
                "type": "datepicker",
                "action_id": "end_date_action"
            }
        },
        {
            "type": "input",
            "block_id": "start_time_picker",
            "label": {
                "type": "plain_text",
                "text": "Start Time Picker",
                "emoji": True
            },
            "element": {
                "type": "timepicker",
                "action_id": "start_time_picker_action"
            }
        },
        {
            "type": "input",
            "block_id": "end_time_picker",
            "label": {
                "type": "plain_text",
                "text": "End Time Picker",
                "emoji": True
            },
            "element": {
                "type": "timepicker",
                "action_id": "end_time_picker_action"
            }
        },
        {
            "type": "input",
            "block_id": "p1_customer_affected",
            "label": {
                "type": "plain_text",
                "text": "P1 Customer Affected"
            },
            "element": {
                "type": "checkboxes",
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "P1 customer affected"
                        },
                        "value": "p1_customer_affected"
                    }
                ],
                "action_id": "p1_customer_affected_action"
            }
        },
        {
            "type": "input",
            "block_id": "suspected_affected_components",
            "label": {
                "type": "plain_text",
                "text": "Suspected Affected Components"
            },
            "element": {
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select components"
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Component 1"
                        },
                        "value": "component_1"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Component 2"
                        },
                        "value": "component_2"
                    }
                ],
                "action_id": "suspected_affected_components_action"
            }
        },
        {
            "type": "input",
            "block_id": "description",
            "label": {
                "type": "plain_text",
                "text": "Description"
            },
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "action_id": "description_action",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter description"
                }
            }
        },
        {
            "type": "input",
            "block_id": "message_for_sp",
            "label": {
                "type": "plain_text",
                "text": "Message for SP"
            },
            "element": {
                "type": "plain_text_input",
                "multiline": True,
                "action_id": "message_for_sp_action",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Enter message"
                }
            }
        },
        {
            "type": "input",
            "block_id": "flags_for_statuspage_notification",
            "label": {
                "type": "plain_text",
                "text": "Flags"
            },
            "element": {
                "type": "checkboxes",
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Statuspage Notification"
                        },
                        "value": "statuspage_notification"
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Separate Channel Creation"
                        },
                        "value": "separate_channel_creation"
                    }
                ],
                "action_id": "flags_for_statuspage_notification_action"
            }
        }
    ]
    }
 
 
