import json
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
import time

project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.lambda_handlers.commands.commands import handler

os.environ['IS_LOCAL_TEST'] = 'true'
print(f"IS_LOCAL_TEST environment variable set to: {os.environ.get('IS_LOCAL_TEST')}")


class MockLambdaContext:
    def __init__(self):
        self.function_name = "test-function"
        self.function_version = "test-version"
        self.invoked_function_arn = "test-arn"
        self.memory_limit_in_mb = 128
        self.aws_request_id = "test-request-id"
        self.log_group_name = "test-log-group"
        self.log_stream_name = "test-log-stream"

async def test_commands():
    mock_context = MockLambdaContext()
    
    commands = [
        '/create-incident',
        '/get-incident',
        '/update-incident'
    ]
    
    for command in commands:
        print(f"\n=== Testing {command} ===")
        
        # Create form-encoded body
        body_dict = {
            "command": command,
            "trigger_id": "123.456",
            "token": "test_token",
            "user_id": "test_user",
            "team_id": "test_team"
        }
        
        # Create test event
        test_event = {
            "headers": {
                "x-slack-signature": "v0=test",
                "x-slack-request-timestamp": str(int(time.time())),
                "Content-Type": "application/x-www-form-urlencoded"
            }
        }
        
        # Encode the body
        test_event['body'] = urlencode(body_dict).encode("utf-8")
        
        try:
            response = await handler(test_event, mock_context)
            print(f"Status Code: {response['statusCode']}")
            print(f"Response Body: {response['body']}")
        except Exception as e:
            print(f"Error testing {command}: {str(e)}")

if __name__ == "__main__":
    # Set environment variables
    os.environ['IS_LOCAL_TEST'] = 'true'
    os.environ['SLACK_BOT_TOKEN'] = 'test_token'
    os.environ['SLACK_VERIFICATION_TOKEN'] = 'test_token'
    os.environ['SLACK_SIGNING_SECRET'] = 'test_signing_secret'
    
    asyncio.run(test_commands())