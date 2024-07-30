from fastapi import HTTPException,status
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.config import settings

slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)


async def get_channel_id(channel_name: str) -> str:
    try:
        response = slack_client.conversations_list()
        channels = response["channels"]
        for channel in channels:
            if channel["name"] == channel_name:
                return channel["id"]
    except SlackApiError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Slack API error: {e.response['error']}")



async def post_message_to_slack(channel_id: str, message: str):
    try:
        slack_client.chat_postMessage(
            channel=channel_id,
            text=message
        )
    except SlackApiError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Slack API error: {e.response['error']}")




async def create_slack_channel(channel_name: str) -> str:
    try:
        response = slack_client.conversations_create(
            name=channel_name,
            is_private=True  #  True if I  want a private channel
        )
        channel_id = response["channel"]["id"]
        return channel_id
    except SlackApiError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Slack API error: {e.response['error']}")
    
    
