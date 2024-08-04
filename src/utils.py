import os
import json
from fastapi import HTTPException, status, Request, Depends, Header
from config import get_settings, Settings
import hmac
import hashlib
import json
import os
import time


settings = get_settings()


async def load_options_from_file(file_path: str) -> dict:
    assert os.path.exists(file_path), f"File {file_path} does not exist."
    with open(file_path, "r") as f:
        return json.load(f)


# Load options when the application starts
options = None


async def initialize_options():
    global options
    options = await load_options_from_file(
        os.path.join(os.path.dirname(__file__), "options.json")
    )


async def verify_slack_request(
    body: bytes,
    x_slack_signature,
    x_slack_request_timestamp,
    settings
):
    if not x_slack_request_timestamp or not x_slack_signature:
        raise HTTPException(status_code=400, detail="Missing request signature")

    current_timestamp = int(time.time())
    if abs(current_timestamp - int(x_slack_request_timestamp)) > 60 * 5:
        raise HTTPException(status_code=400, detail="Request timestamp is too old")

    sig_base = f"v0:{x_slack_request_timestamp}:{body.decode()}"
    my_signature = (
        "v0="
        + hmac.new(
            settings.SLACK_SIGNING_SECRET.encode(), sig_base.encode(), hashlib.sha256
        ).hexdigest()
    )

    # print(f"Received signature: {x_slack_signature}")
    # print(f"Computed signature: {my_signature}")
    # print(f"Sig base: {sig_base}")

    if not hmac.compare_digest(my_signature, x_slack_signature):
        print("Signature mismatch")
        raise HTTPException(
            status_code=400, detail="Invalid request signature is detected"
        )

    print("Signature verified")


async def slack_challenge_parameter_verification(request: Request):
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to parse JSON body: {str(e)}"
        ) from e
    # Handle URL verification with slack to accept the challenge parameter
    if body.get("type") == "url_verification":
        return {"challenge": body.get("challenge")}


async def create_modal_view(callback_id: str) -> dict:
    return {
        "type": "modal",
        "callback_id": "incident_form",
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
                    "type": "multi_static_select",
                    "placeholder": {"type": "plain_text", "text": "Select products"},
                    "options": [
                        # Old hardcoded code-keeping it for future,just in case something breaks
                        # {
                        #     "text": {
                        #         "type": "plain_text",
                        #         "text": "BetBuilder"
                        #     },
                        #     "value": "BetBuilder"
                        # },
                        # {
                        #     "text": {
                        #         "type": "plain_text",
                        #         "text": "BetVision"
                        #     },
                        #     "value": "BetVision"
                        # }
                        {
                            "text": {"type": "plain_text", "text": item["text"]},
                            "value": item["value"],
                        }
                        for item in options["affected_products"]
                    ],
                    "action_id": "affected_products_action",
                },
            },
            {
                "type": "input",
                "block_id": "severity",
                "label": {"type": "plain_text", "text": "Severity"},
                "element": {
                    "type": "multi_static_select",
                    "placeholder": {"type": "plain_text", "text": "Select severity"},
                    "options": [
                        # {
                        #     "text": {
                        #         "type": "plain_text",
                        #         "text": "Major"
                        #     },
                        #     "value": "Major"
                        # },
                        # {
                        #     "text": {
                        #         "type": "plain_text",
                        #         "text": "Minor"
                        #     },
                        #     "value": "Minor"
                        # },
                        # {
                        #     "text": {
                        #         "type": "plain_text",
                        #         "text": "Moderate"
                        #     },
                        #     "value": "Moderate"
                        # },
                        # {
                        #     "text": {
                        #         "type": "plain_text",
                        #         "text": "No issue"
                        #     },
                        #     "value": "No issue"
                        # },
                        # {
                        #     "text": {
                        #         "type": "plain_text",
                        #         "text": "None"
                        #     },
                        #     "value": "None"
                        # }
                        {
                            "text": {"type": "plain_text", "text": item["text"]},
                            "value": item["value"],
                        }
                        for item in options["severity"]
                    ],
                    "action_id": "severity_action",
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
                            "text": {"type": "plain_text", "text": item["text"]},
                            "value": item["value"],
                        }
                        for item in options["suspected_owning_team"]
                    ],
                    "action_id": "suspected_owning_team_action",
                },
            },
            {
                "type": "input",
                "block_id": "start_time",
                "label": {"type": "plain_text", "text": "Start Time", "emoji": True},
                "element": {"type": "datepicker", "action_id": "start_date_action"},
            },
            {
                "type": "input",
                "block_id": "end_time",
                "label": {"type": "plain_text", "text": "End Time", "emoji": True},
                "element": {"type": "datepicker", "action_id": "end_date_action"},
            },
            {
                "type": "input",
                "block_id": "start_time_picker",
                "label": {
                    "type": "plain_text",
                    "text": "Start Time Picker",
                    "emoji": True,
                },
                "element": {
                    "type": "timepicker",
                    "action_id": "start_time_picker_action",
                },
            },
            {
                "type": "input",
                "block_id": "end_time_picker",
                "label": {
                    "type": "plain_text",
                    "text": "End Time Picker",
                    "emoji": True,
                },
                "element": {
                    "type": "timepicker",
                    "action_id": "end_time_picker_action",
                },
            },
            {
                "type": "input",
                "block_id": "p1_customer_affected",
                "label": {"type": "plain_text", "text": "P1 Customer Affected"},
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
                    "action_id": "p1_customer_affected_action",
                },
            },
            {
                "type": "input",
                "block_id": "suspected_affected_components",
                "label": {
                    "type": "plain_text",
                    "text": "Suspected Affected Components",
                },
                "element": {
                    "type": "static_select",
                    "placeholder": {"type": "plain_text", "text": "Select components"},
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": item["text"]},
                            "value": item["value"],
                        }
                        for item in options["suspected_affected_components"]
                    ],
                    "action_id": "suspected_affected_components_action",
                },
            },
            {
                "type": "input",
                "block_id": "description",
                "label": {"type": "plain_text", "text": "Description"},
                "element": {
                    "type": "plain_text_input",
                    "multiline": True,
                    "action_id": "description_action",
                    "placeholder": {"type": "plain_text", "text": "Enter description"},
                },
            },
            {
                "type": "input",
                "block_id": "message_for_sp",
                "label": {"type": "plain_text", "text": "Message for SP"},
                "element": {
                    "type": "plain_text_input",
                    "multiline": True,
                    "action_id": "message_for_sp_action",
                    "placeholder": {"type": "plain_text", "text": "Enter message"},
                },
            },
            {
                "type": "input",
                "block_id": "flags_for_statuspage_notification",
                "label": {"type": "plain_text", "text": "Flags"},
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
                    "action_id": "flags_for_statuspage_notification_action",
                },
            },
        ],
    }
