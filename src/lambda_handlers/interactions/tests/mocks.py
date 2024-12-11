# src/lambda_handlers/interactions/tests/mocks.py
from unittest.mock import AsyncMock

class MockJira:
    @staticmethod
    async def create_ticket(*args, **kwargs):
        return {
            "key": "TEST-123",
            "id": "10000",
            "self": "https://test-jira.com/issue/TEST-123"
        }

class MockSlack:
    @staticmethod
    async def open_modal(*args, **kwargs):
        return {"ok": True}
    
    @staticmethod
    async def create_channel(*args, **kwargs):
        return "test-channel-id"
    
    @staticmethod
    async def post_message(*args, **kwargs):
        return {"ok": True}