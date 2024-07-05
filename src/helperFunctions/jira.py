import base64
import json
import requests
from fastapi import HTTPException, status
from src.config import settings

# Assuming `Settings` and environment variables are correctly defined
# and loaded from .env as shown previously

def get_jira_auth():
    auth_str = f"{settings.jira_email}:{settings.jira_api_key}"
    base_64_auth = base64.b64encode(auth_str.encode()).decode()
    return base_64_auth



def create_jira_ticket(incident: dict):
    jira_url = f"{settings.jira_server}/rest/api/2/issue"
    
    base_64_auth = get_jira_auth()
    headers = {
        'Authorization': f"Basic {base_64_auth}",
        'Content-Type': 'application/json'
    }

    issue_dict = {
        'fields': {
            'project': {'key': 'SO'},
            'summary': f"Incident: {incident['affected_products']} - {incident['severity']}",
            'description': (
                f"Description: {incident['description']}\n"
                f"Severity: {incident['severity']}\n"
                f"Affected Products: {incident['affected_products']}\n"
                f"Suspected Owning Team: {incident['suspected_owning_team']}\n"
                f"Start Time: {incident['start_time']}\n"
                f"Customer Affected: {'Yes' if incident['p1_customer_affected'] else 'No'}\n"
                f"Suspected Affected Components: {incident['suspected_affected_components']}\n"
                f"Message for SP: {incident.get('message_for_sp', 'N/A')}\n"
                f"Status Page Notification: {'Yes' if incident['statuspage_notification'] else 'No'}\n"
                f"Separate Channel Creation: {'Yes' if incident['separate_channel_creation'] else 'No'}"
            ),
            'issuetype': {'name': 'Service Outage'},  
            'reporter': {'name': settings.jira_email},
            
            #Custom fields
            'customfield_12608': incident['start_time'].isoformat(),
            # 'customfield_16130': incident['affected_products'],
        }
    }

    print("Sending request to Jira API")
    print(f"URL: {jira_url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(issue_dict, indent=2)}")
    
    try:
        response = requests.post(jira_url, headers=headers, json=issue_dict)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content.decode()}")
        response.raise_for_status()  # Raise an exception for HTTP errors
        issue = response.json()
        return issue
    except requests.exceptions.HTTPError as http_err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Jira API error: {response.text}")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))