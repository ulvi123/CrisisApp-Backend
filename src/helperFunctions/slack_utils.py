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
        )

        logger.info(f"Slack API response in create_slack_channel: {response}")

        if response["ok"]:
            channel_id = response["channel"]["id"]
            logger.info(f"Channel created successfully. Channel ID: {channel_id}")
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
        if e.response["error"] == "rate_limited":
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
