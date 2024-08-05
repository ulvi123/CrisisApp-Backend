# import base64
# import json
# import requests
# from fastapi import HTTPException, status
# from config import get_settings, Settings
# from src.models import Incident  
# from src import schemas
# from src.schemas import IncidentResponse,IncidentCreate
# import logging
# import httpx

# # Setting up logging
# # logging.basicConfig(level=logging.DEBUG)
# # logger = logging.getLogger(__name__)


# settings  = get_settings()

# def get_jira_auth():
#     auth_str = f"{settings.jira_email}:{settings.jira_api_key}"
#     base_64_auth = base64.b64encode(auth_str.encode()).decode()
#     return base_64_auth

# def create_jira_ticket(incident:dict):
#     jira_url = f"{settings.jira_server}/rest/api/2/issue"
#     base_64_auth = get_jira_auth()
#     headers = {
#         'Authorization': f"Basic {base_64_auth}",
#         'Content-Type': 'application/json'
#     }

#     # Convert times to ISO format, if they are not None
#     start_time_iso = incident.start_time.isoformat() if incident.start_time else None
#     end_time_iso = incident.end_time.isoformat() if incident.end_time else None
#     suspected_owning_team = [team for team in incident.suspected_owning_team]
#     affected_products = [product for product in incident.affected_products]
#     suspected_affected_components = [component for component in incident.suspected_affected_components]
#     severity = [severity for severity in incident.severity]
    
#     issue_dict = {
#         'fields': {
#             'project': {'key': 'SO'},
#             'summary': f"Incident: {', '.join(affected_products)} - {incident.description}",
#             'description': (
#                 f"Description: {incident.description}\n"
#                 f"Severity: {incident.severity}\n"
#                 f"Affected Products: {', '.join(affected_products)}\n"
#                 f"Suspected Owning Team: {', '.join(suspected_owning_team)}\n"
#                 f"Start Time: {incident.start_time.isoformat()}\n"
#                 f"End Time: {incident.end_time.isoformat()}\n"
#                 f"Customer Affected: {'Yes' if incident.p1_customer_affected else 'No'}\n"
#                 f"Suspected Affected Components: {', '.join(suspected_affected_components)}\n"
#                 f"Message for SP: {incident.message_for_sp or 'N/A'}\n"
#                 f"Status Page Notification: {'Yes' if incident.statuspage_notification else 'No'}\n"
#                 f"Separate Channel Creation: {'Yes' if incident.separate_channel_creation else 'No'}"
#             ),
#             'issuetype': {'name': 'Service Outage'},
#             'reporter': {'name': settings.jira_email},

#             # Custom fields
#             'customfield_12608': start_time_iso,
#             'customfield_12607': end_time_iso,
#             'customfield_17273': [{'value': team} for team in suspected_owning_team],
#             'customfield_17272': [{'value': product} for product in affected_products],
#             'customfield_11201': [{'value':severity} for severity in severity]
#         }
#     }

#     # Print for debugging
#     print(f"Jira Payload - Affected Products: {issue_dict['fields']['customfield_17272']}")
#     print(f"Jira Payload - Suspected Owning Team: {issue_dict['fields']['customfield_17273']}")
#     print("Sending request to Jira API")
#     print(f"URL: {jira_url}")
#     print(f"Headers: {headers}")
#     print(f"Payload: {json.dumps(issue_dict, indent=2)}")

#     try:
#         response = requests.post(jira_url, headers=headers, json=issue_dict)
#         print(f"Response status code: {response.status_code}")
#         print(f"Response content: {response.content.decode()}")
#         response.raise_for_status()  # Raise an exception for HTTP errors
#         issue = response.json()
#         return issue
#     except requests.exceptions.HTTPError as http_err:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Jira API error: {response.text}") from http_err
#     except Exception as e:
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
    
   


import base64
import json
import logging
import requests
from fastapi import HTTPException, status,Depends
from config import Settings, get_settings
from src import schemas

settings = get_settings()

def get_jira_auth():
    auth_str = f"{settings.jira_email}:{settings.jira_api_key}"
    base_64_auth = base64.b64encode(auth_str.encode()).decode()
    return base_64_auth

def create_jira_ticket(incident:schemas.IncidentCreate):
    jira_url = f"{settings.jira_server}/rest/api/2/issue"
    base_64_auth = get_jira_auth()
    headers = {
        'Authorization': f"Basic {base_64_auth}",
        'Content-Type': 'application/json'
    }
    
    
    # Convert times to ISO format, if they are not None
    start_time_iso = incident.start_time.isoformat() if incident.start_time else None
    end_time_iso = incident.end_time.isoformat() if incident.end_time else None
    suspected_owning_team = [team for team in incident.suspected_owning_team]
    affected_products = [product for product in incident.affected_products]
    # suspected_affected_components = [component for component in incident.suspected_affected_components]
    severity = [severity for severity in incident.severity]

    issue_dict = {
        'fields': {
            'project': {'key': 'SO'},  # Ensure this is the correct project key
            'summary': f"Incident: {incident.affected_products} - {incident.severity}",
            'description': (
                f"Description: {incident.description}\n"
                f"Severity: {', '.join(incident.severity)}\n"
                f"Affected Products: {', '.join(incident.affected_products)}\n"
                f"Suspected Owning Team: {', '.join(incident.suspected_owning_team)}\n"
                f"Start Time: {incident.start_time}\n"
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
            # 'customfield_11201': [{'value':severity} for severity in severity]
        }
    }
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

        # Return the issue key
        # issue_key = issue.get('key')
        # if not issue_key:
        #     raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve issue key from Jira response")

        # return {"issue_key": issue_key}

    except requests.exceptions.HTTPError as http_err:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Jira API error: {response.text}") from http_err
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e
