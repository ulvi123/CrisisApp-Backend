import hmac
import hashlib
import time
import urllib.parse
import requests


from config import get_settings, Settings

settings = get_settings()


form_data = {
    "token": "Djk1qAbWR6meez3Y0lVSC2KS",
    "team_id": "T0001",
    "team_domain": "example",
    "channel_id": "C2147483705",
    "channel_name": "test",
    "user_id": "U2147483697",
    "user_name": "Steve",
    "command": "/create-incident",
    "text": "incident details",
    "response_url": "https://hooks.slack.com/commands/1234/5678",
    "trigger_id": "13345224609.738474920.8088930838d88f008e0",
}

# URL-encode the form data
request_body = urllib.parse.urlencode(
    form_data
)


SLACK_SIGNING_SECRET = settings.SLACK_SIGNING_SECRET


timestamp = str(int(time.time()))


# Create the basestring
sig_base = f"v0:{timestamp}:{request_body}"

# Create the signature
my_signature = (
    "v0="
    + hmac.new(
        SLACK_SIGNING_SECRET.encode(), sig_base.encode(), hashlib.sha256
    ).hexdigest()
)

headers = {
    "x_slack_request_timestamp": timestamp,
    "x_slack_signature": my_signature,
    "Content-Type": "application/x-www-form-urlencoded",
}

response = requests.post(
    "https://8825-85-253-101-83.ngrok-free.app/slack/commands",
    headers=headers,
    data=request_body,
)

print("Status Code:", response.status_code)
print("Response Body:", response.text)

print("x_slack_request_timestamp", timestamp)
print("x_slack_signature", my_signature)
print("request-body:", request_body)
