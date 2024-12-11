import json
import asyncio
import os
import sys
from pathlib import Path
import time
import urllib
from unittest.mock import AsyncMock, patch,MagicMock

project_root = str(Path(__file__).parent.parent.parent)
sys.path.append(project_root)

from src.lambda_handlers.interactions.interactions import handler
from src.lambda_handlers.interactions.tests.mocks import MockJira, MockSlack


class MockLambdaContext:
    def __init__(self):
        self.function_name = "test-function"
        self.function_version = "test-version"
        self.invoked_function_arn = "test-arn"
        self.memory_limit_in_mb = 128
        self.aws_request_id = "test-request-id"
        self.log_group_name = "test-log-group"
        self.log_stream_name = "test-log-stream"


@patch('src.helperFunctions.jira.create_jira_ticket', AsyncMock(return_value={"key": "TEST-123"}))
@patch('src.helperFunctions.slack_utils.open_slack_response_modal', AsyncMock(return_value={"ok": True}))
@patch('src.helperFunctions.slack_utils.create_slack_channel', AsyncMock(return_value="test-channel-id"))
@patch('src.helperFunctions.slack_utils.post_message_to_slack', AsyncMock(return_value={"ok": True}))


async def test_incident_form_submission():
    mock_context = MockLambdaContext()
    
    # Test payload with minimal required fields
    form_payload = {
        "type": "view_submission",
        "token": "test_token",
        "trigger_id": "test_trigger",
        "user": {"id": "test_user"},
        "view": {
            "callback_id": "incident_form",
            "state": {
                "values": {
                    "start_time": {"start_date_action": {"selected_date": "2024-12-10"}},
                    "start_time_picker": {"start_time_picker_action": {"selected_time": "10:00"}},
                    "end_time": {"end_date_action": {"selected_date": "2024-12-10"}},
                    "end_time_picker": {"end_time_picker_action": {"selected_time": "11:00"}},
                    "so_number": {"so_number_action": {"value": "SO-123"}},
                    "affected_products": {
                        "affected_products_action": {
                            "selected_options": [{"value": "test-product"}]
                        }
                    },
                    "suspected_owning_team": {
                        "suspected_owning_team_action": {
                            "selected_options": [{"value": "test-team"}]
                        }
                    },
                    "severity": {
                        "severity_action": {
                            "selected_option": {"value": "SEV1"}
                        }
                    },
                    "description": {
                        "description_action": {
                            "value": "Test incident description"
                        }
                    }
                }
            }
        }
    }

    # Create test event
    test_event = {
        "headers": {
            "x-slack-signature": "v0=test",
            "x-slack-request-timestamp": str(int(time.time())),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        "body": f"payload={urllib.parse.quote(json.dumps(form_payload))}"
    }
    
    print("\n=== Testing Incident Form Submission ===")

    try:
        response = await handler(test_event, mock_context)
        print(f"📝 Response Status Code: {response['statusCode']}")
        print(f"📝 Response Body: {response['body']}")
        
        # Assertions
        assert response['statusCode'] == 200, "❌ Expected 200 status code"
        response_body = json.loads(response['body'])
        assert response_body['response_action'] == 'clear', "❌ Expected clear response action"
        
        print("✅ Incident form test completed successfully")
        
    except Exception as e:
        print(f"❌ Incident form test failed: {str(e)}")
        import traceback
        print(traceback.format_exc())

@patch('httpx.AsyncClient.post')
async def test_lookup_form_submission(mock_post):
    mock_context = MockLambdaContext()
    
    # Mock Slack API response
    mock_post.return_value.json.return_value = {"ok": True}
    mock_post.return_value.status_code = 200

    # Test payload for lookup
    form_payload = {
        "type": "view_submission",
        "token": "test_token",
        "trigger_id": "test_trigger",
        "user": {"id": "test_user"},
        "view": {
            "callback_id": "so_lookup_form",
            "state": {
                "values": {
                    "so_number": {
                        "so_number_action": {
                            "value": "SO-123"
                        }
                    }
                }
            }
        }
    }

    # Create test event
    test_event = {
        "headers": {
            "x-slack-signature": "v0=test",
            "x-slack-request-timestamp": str(int(time.time())),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        "body": f"payload={urllib.parse.quote(json.dumps(form_payload))}"
    }

    print("\n=== Testing SO Lookup Form ===")
    print("Testing with SO number: SO-123")

    try:
        response = await handler(test_event, mock_context)
        print(f"📝 Response Status Code: {response['statusCode']}")
        print(f"📝 Response Body: {response['body']}")
        
        # Test validation
        response_body = json.loads(response['body'])
        assert response['statusCode'] == 200, "❌ Expected 200 status code"
        assert 'response_action' in response_body, "❌ Expected response_action in body"
        
        if 'errors' in response_body:
            print(f"⚠️ Form returned errors: {response_body['errors']}")
        else:
            print("✅ SO lookup form processed successfully")

    except Exception as e:
        print(f"❌ SO lookup form test failed: {str(e)}")
        import traceback
        print(traceback.format_exc())

@patch('src.helperFunctions.status_page.update_statuspage_incident_status')
async def test_statuspage_update_form_submission(mock_update_statuspage):
    mock_context = MockLambdaContext()
    
    # Mock the database query
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(so_number="SO-123")
    
    # Mock the update_statuspage_incident_status function
    mock_update_statuspage.return_value = {"status": "success"}
    
    # Test payload for statuspage update
    form_payload = {
        "type": "view_submission",
        "token": "test_token",
        "trigger_id": "test_trigger",
        "user": {"id": "test_user"},
        "view": {
            "callback_id": "statuspage_update",
            "state": {
                "values": {
                    "so_number": {"so_number_action": {"value": "SO-123"}},
                    "status_update_block": {"status_action": {"selected_option": {"value": "resolved"}}},
                    "additional_info_block": {"additional_info_action": {"value": "Test update"}}
                }
            }
        }
    }

    # Create test event
    test_event = {
        "headers": {
            "x-slack-signature": "v0=test",
            "x-slack-request-timestamp": str(int(time.time())),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        "body": f"payload={urllib.parse.quote(json.dumps(form_payload))}"
    }

    print("\n=== Testing Statuspage Update Form ===")
    print("Testing with SO number: SO-123")

    try:
        response = await handler(test_event, mock_context)
        print(f"📝 Response Status Code: {response['statusCode']}")
        print(f"📝 Response Body: {response['body']}")
        
        # Test validation
        assert response['statusCode'] == 200, "❌ Expected 200 status code"
        response_body = json.loads(response['body'])
        assert 'response_action' in response_body, "❌ Expected response_action in body"
        
        if 'errors' in response_body:
            print(f"⚠️ Form returned errors: {response_body['errors']}")
        else:
            print("✅ Statuspage update form processed successfully")

    except Exception as e:
        print(f"❌ Statuspage update form test failed: {str(e)}")
        import traceback
        print(traceback.format_exc())




if __name__ == "__main__":
    print("🔧 Setting up test environment...")
    os.environ['IS_LOCAL_TEST'] = 'true'
    os.environ['SLACK_BOT_TOKEN'] = 'test_token'
    os.environ['SLACK_VERIFICATION_TOKEN'] = 'test_token'
    os.environ['SLACK_SIGNING_SECRET'] = 'test_signing_secret'
    
    # Run both tests
    asyncio.run(test_incident_form_submission())
    asyncio.run(test_lookup_form_submission())
    asyncio.run(test_statuspage_update_form_submission())