import asyncio
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List
from fastapi import HTTPException, status, Depends
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import get_settings, Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)

executor = ThreadPoolExecutor(max_workers=10)


async def run_in_executor(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, lambda: (func(*args, **kwargs)))

async def test_slack_integration(slack_settings: Settings = Depends(get_settings)):
    try:
        await post_message_to_slack(
            slack_settings.SLACK_GENERAL_OUTAGES_CHANNEL, "Testing Slack integration"
        )
        logger.info("Slack integration test successful")
    except SlackApiError as e:
        logger.error(f"Test Slack Integration Error: {str(e)}")

async def get_channel_id(channel_name: str) -> str:
    try:
        response = await run_in_executor(slack_client.conversations_list)
        if response["ok"]:
            for channel in response["channels"]:
                if channel["name"] == channel_name:
                    logger.info(f"Channel already exists. Channel ID: {channel['id']}")
                    return channel["id"]
        await asyncio.sleep(1)
        return None
    except SlackApiError as e:
        logger.error(f"Slack API error in get_channel_id: {e.response['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slack API error: {e.response['error']}",
        ) from e

# check the channel not found bug- the root cause of it
async def post_message_to_slack(channel_id: str, message: str):
    try:
        response = await run_in_executor(
            slack_client.chat_postMessage, channel=channel_id, text=message
        )

        if response["ok"]:
            logger.info(f"Message posted to Slack channel ID {channel_id}")
            return response
        logger.error(
            f"Slack API error in post_message_to_slack: {response['error']}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slack API error: {response['error']}",
        )
    except SlackApiError as e:
        logger.error(f"Slack API error in post_message_to_slack: {e.response['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slack API error: {e.response['error']}",
        ) from e

async def create_slack_channel(channel_name: str) -> str:
    try:
        # Check if the channel already exists
        channel_id = await get_channel_id(channel_name)
        if channel_id:
            logger.info(f"Channel already exists. Channel ID: {channel_id}")
            return channel_id

        # If the channel does not exist, create a new one
        unique_channel_name = f"{channel_name}-{int(time.time())}"
        response = await run_in_executor(
            slack_client.conversations_create,
            name=unique_channel_name,
            is_private=False,
            is_group=False,
        )

        logger.info(f"Slack API response in create_slack_channel: {response}")

        if response["ok"]:
            channel_id = response["channel"]["id"]
            logger.info(f"Channel created successfully. Channel ID: {channel_id}")
            
            #Enabling the bot to join the channel when it is created
            await run_in_executor(slack_client.conversations_join, channel=channel_id)
            logger.info(f"Bot enabled to join the channel: {channel_id}")
            await asyncio.sleep(2)
            return channel_id
        

        logger.error(
            f"Failed to create channel. Error: {response.get('error', 'Unknown error')}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create Slack channel: {response.get('error', 'Unknown error')}",
        )

    except SlackApiError as e:
        logger.error(f"Slack API error in create_slack_channel: {e.response['error']}")
        logger.error(f"Full error response: {e.response}")
        if e.response["error"] == "ratelimited":
            retry_after = int(e.response["headers"].get("Retry-After", 1))
            logger.info(f"Rate limited. Retrying after {retry_after} seconds")
            await asyncio.sleep(retry_after)
            return await create_slack_channel(channel_name)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slack API error: {e.response['error']}",
        ) from e

    except Exception as e:
        logger.exception(f"Unexpected error in create_slack_channel: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e

async def open_slack_response_modal(trigger_id:str,modal_type:dict,incident_data:dict):
    try:
        modal_payload=None
        if modal_type == "success":
            if not incident_data:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                   detail="Incident data is required for success modal")
            modal_payload = {
                "type": "modal",
                "callback_id": "incident_creation_success",
                "title": {
                    "type": "plain_text",
                    "text": "Incident Created"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*✅ Incident Created Successfully!*"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Incident Number:*"
                            },
                            {
                                "type": "plain_text",
                                "text": f"{incident_data.get('so_number')}"
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Severity:*"
                            },
                            {
                                "type": "plain_text",
                                "text": f"{incident_data.get('severity')}"
                            }
                        ]
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Track this incident further using the link below to Jira:"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "📄 View Jira Ticket",
                                    "emoji": True
                                },
                                "url": f"{settings.jira_server}/browse/{incident_data.get('so_number')}",
                                "action_id": "view_jira"
                            }
                        ]
                    }
                ]
            }
            
        elif modal_type == "error":
            modal_payload = {
                "type": "modal",
                "callback_id": "incident_creation_error",
                "title": {
                    "type": "plain_text",
                    "text": "Error"
                },
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "❌ *Error Creating Incident*"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"An error occurred while creating the incident:\n\n{incident_data.get('error_message', 'Unknown error occurred')}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Please try again or contact support if the issue persists."
                        }
                    }
                ]
            }
            
        else:
            raise ValueError(f"Invalid modal type: {modal_type}")
        
        #Opening the modal
        response = await run_in_executor(
            slack_client.views_open,
            trigger_id=trigger_id,
            view=modal_payload
        )
        
        if response['ok']:
            logger.info(f"Successfully opened {modal_type} modal in slack")
            return response
        else:
            logger.error(f"slack api error in open_slack_response_modal: {response['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Slack API error: {response['error']}",
            )
        
    except SlackApiError as e:
        logger.error(f"Slack API error in open_slack_response_modal: {e.response['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Slack API error: {e.response['error']}",
        )
    except ValueError as e:
        logger.error(f"Value error when opening modal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error when opening {modal_type} modal: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}"
        )