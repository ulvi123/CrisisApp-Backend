import base64
import json
import requests
from fastapi import HTTPException, status
from src.config import settings
from src.models import Incident  # Assuming Incident model is defined correctly

def get_jira_auth():
    auth_str = f"{settings.jira_email}:{settings.jira_api_key}"
    base_64_auth = base64.b64encode(auth_str.encode()).decode()
    return base_64_auth

def create_jira_ticket(incident: Incident):
    jira_url = f"{settings.jira_server}/rest/api/2/issue"
    base_64_auth = get_jira_auth()
    headers = {
        'Authorization': f"Basic {base_64_auth}",
        'Content-Type': 'application/json'
    }

    # Convert times to ISO format, if they are not None
    start_time_iso = incident.start_time.isoformat() if incident.start_time else None
    end_time_iso = incident.end_time.isoformat() if incident.end_time else None

    # Prepare fields for multi-select options
    owning_team = [{'value': team} for team in incident.suspected_owning_team]
    products_affected = [{'value': product} for product in incident.affected_products]

    issue_dict = {
        'fields': {
            'project': {'key': 'SO'},
            'summary': f"Incident: {', '.join(incident.affected_products)} - {incident.description}",
            'description': (
                f"Description: {incident.description}\n"
                f"Severity: {incident.severity}\n"
                f"Affected Products: {', '.join(incident.affected_products)}\n"
                f"Suspected Owning Team: {', '.join(incident.suspected_owning_team)}\n"
                f"Start Time: {incident.start_time}\n"
                f"End Time: {incident.end_time}\n"
                f"Customer Affected: {'Yes' if incident.p1_customer_affected else 'No'}\n"
                f"Suspected Affected Components: {', '.join(incident.suspected_affected_components)}\n"
                f"Message for SP: {incident.message_for_sp or 'N/A'}\n"
                f"Status Page Notification: {'Yes' if incident.statuspage_notification else 'No'}\n"
                f"Separate Channel Creation: {'Yes' if incident.separate_channel_creation else 'No'}"
            ),
            'issuetype': {'name': 'Service Outage'},  
            'reporter': {'name': settings.jira_email},
            
            # Custom fields
            'customfield_12608': start_time_iso,
            'customfield_12607': end_time_iso,
            'customfield_17271': owning_team,
            'customfield_17272': products_affected,
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
