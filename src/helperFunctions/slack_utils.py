import asyncio
import time
from fastapi import HTTPException,status
from slack_sdk import WebClient # type: ignore
from slack_sdk.errors import SlackApiError # type: ignore
from src.config import settings

slack_client = WebClient(token=settings.SLACK_BOT_TOKEN)

# Test minimal functionality
async def test_slack_integration():
    try:
        # Post a message to an existing channel
        await post_message_to_slack(settings.SLACK_GENERAL_OUTAGES_CHANNEL, "Testing Slack integration")
    except Exception as e:
        print(f"Test Slack Integration Error: {str(e)}")


async def get_channel_id(channel_name: str) -> str:
        try:
            response = slack_client.conversations_list()
            for channel in response['channels']:	
                if channel['name'] == channel_name:
                    print(f"Channel already exists. Channel ID: {channel['id']}")
                    return channel['id']
            time.sleep(3)# Sleep for 3 seconds before retrying
        
            return None
        except SlackApiError as e:
            print(f"Slack API error: {e.response['error']}")  # Logging the error
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Slack API error: {e.response['error']}")
        


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
        print(f"Message posted to Slack channel ID {channel_id}")
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}")  # Logging the error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Slack API error: {e.response['error']}")




async def create_slack_channel(channel_name: str) -> str:
    try:
        #Check if channel already exists
        channel_id = await get_channel_id(channel_name)
        if channel_id:
            print(f"Channel already exists. Channel ID: {channel_id}")
            return channel_id
        
        #If the channel does not exist, create a new one
        unique_channel_name = f"{channel_name}-{int(time.time())}"
        response =  slack_client.conversations_create(
            name=unique_channel_name,
            is_private=False
        )
        
        await asyncio.sleep(10)
        channel_id = response["channel"]["id"]
        print(f"Channel created successfully. Channel ID: {channel_id}")  # Logging channel ID
    
        
        return channel_id
    
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}")  # Logging the error
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Slack API error: {e.response['error']}")
    
