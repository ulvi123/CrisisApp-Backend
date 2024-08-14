import base64
import json
import logging
import requests
from fastapi import HTTPException, status,Depends
from config import Settings, get_settings
from src import schemas

settings = get_settings()

async def get_jira_auth():
    auth_str = f"{settings.jira_email}:{settings.jira_api_key}"
    base_64_auth = base64.b64encode(auth_str.encode()).decode()
    return base_64_auth

async def create_jira_ticket(incident:schemas.IncidentCreate):
    jira_url = f"{settings.jira_server}/rest/api/2/issue"
    base_64_auth = await get_jira_auth()
    headers = {
        'Authorization': f"Basic {base_64_auth}",
        'Content-Type': 'application/json'
    }
    
    
    # Convert times to ISO format, if they are not None
    start_time_iso = incident.start_time.isoformat() if incident.start_time else None
    end_time_iso = incident.end_time.isoformat() if incident.end_time else None
    suspected_owning_team = [team for team in incident.suspected_owning_team]
    affected_products = [product for product in incident.affected_products]
    severity = [severity for severity in incident.severity]

    # issue_dict = {
    #     'fields': {
    #         'project': {'key': 'SO'},  # Ensure this is the correct project key
    #         'summary': f"Incident: {incident.affected_products}",
    #         'description': (
    #             f"Description: {incident.description}\n"
    #             f"Severity: {', '.join(incident.severity)}\n"
    #             f"Affected Products: {', '.join(incident.affected_products)}\n"
    #             f"Suspected Owning Team: {', '.join(incident.suspected_owning_team)}\n"
    #             f"Start Time: {incident.start_time}\n",
    #             f"End Time: {incident.end_time}\n",
    #             f"Customer Affected: {'Yes' if incident.p1_customer_affected else 'No'}\n"
    #             f"Suspected Affected Components: {', '.join(incident.suspected_affected_components)}\n"
    #             f"Message for SP: {incident.message_for_sp}\n"
    #             f"Status Page Notification: {'Yes' if incident.statuspage_notification else 'No'}\n"
    #             f"Separate Channel Creation: {'Yes' if incident.separate_channel_creation else 'No'}"
    #         ),
    #         'issuetype': {'name': 'Service Outage'},  # Adjust issuetype as necessary
    #         'reporter': {'name': settings.jira_email},  # Use the email as the reporter
            
    #         # Custom fields
    #         'customfield_12608': start_time_iso,
    #         'customfield_12607': end_time_iso,
    #         'customfield_17273': [{'value': team} for team in suspected_owning_team],
    #         'customfield_17272': [{'value': product} for product in affected_products],
    #         'customfield_11201': {'value': severity[0]} if severity else None,
    #         # 'customfield_11201': [{'value': severity} for severity in severity],
    #         # 'customfield_16998': [{'value': component} for component in suspected_affected_components]-nuke it
    #         #ASK Yordan what are the exact field IDs or names for these input fields in Jira!
    #     }
    # }
    
    
    issue_dict = {
    'fields': {
        'project': {'key': 'SO'},  # Ensure this is the correct project key
        'summary': f"{incident.start_time} > {incident.severity}> {', '.join(incident.affected_products)} > Outage ",
        'description': (
            f"Description: {incident.description}\n"
            f"Severity: {', '.join(incident.severity)}\n"
            f"Affected Products: {', '.join(incident.affected_products)}\n"
            f"Suspected Owning Team: {', '.join(incident.suspected_owning_team)}\n"
            f"Start Time: {incident.start_time}\n"
            f"End Time: {incident.end_time}\n"
            f"Customer Affected: {'Yes' if incident.p1_customer_affected else 'No'}\n"
            f"Suspected Affected Components: {', '.join(incident.suspected_affected_components)}\n"
            f"Message for SP: {incident.message_for_sp}\n"
            f"Status Page Notification: {'Yes' if incident.statuspage_notification else 'No'}\n"
            f"Separate Channel Creation: {'Yes' if incident.separate_channel_creation else 'No'}"
        ),
        'issuetype': {'name': 'Service Outage'},  # Adjust issuetype as necessary
        'reporter': {'name': settings.jira_email},  # Use the email as the reporter

        # Custom fields
        'customfield_12608': start_time_iso,
        'customfield_12607': end_time_iso,
        'customfield_17273': [{'value': team} for team in suspected_owning_team],
        'customfield_17272': [{'value': product} for product in affected_products],
        'customfield_11201': {'value': severity[0]} if severity else None,
    }
}

    print("Jira Issue Payload:", json.dumps(issue_dict, indent=2))

    print("Sending request to Jira API")
    print(f"URL: {jira_url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(issue_dict, indent=2)}")
    
    try:
        response = requests.post(jira_url, headers=headers, json=issue_dict,timeout=5)
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.content.decode()}")
        response.raise_for_status()  # Raise an exception for HTTP errors
        issue = response.json()
        print(f"Issue created: {issue}")
        return issue

    except requests.exceptions.HTTPError as http_err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Jira API error: {response.text}") from http_err
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
