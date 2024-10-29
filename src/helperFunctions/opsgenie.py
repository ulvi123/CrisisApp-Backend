import requests
from config import settings
from typing import Dict,Tuple
from requests.exceptions import RequestException
import logging


logger = logging.getLogger(__name__)


class OpsGenieError(Exception):
    pass

async def create_alert(incident) -> Dict:
    url = "https://api.opsgenie.com/v2/alerts"
    headers = {
        "Authorization": f"GenieKey {settings.opsgenie_api_key}",
        "Content-Type": "application/json",
    }
    # Updated Opsgenie payload with a more conversational style
    payload = {
        "message": "Service Outage Alert",
        "description": (
            f"A new incident has been created regarding a service outage.\n\n"
            f"Description:\n"
            f"{incident.description}\n"
            f"For more details, you can check the Jira issue here: {settings.jira_server}/browse/{incident.jira_issue_key}"
        ),
        "priority": "P1",
    }
     
    try:
        logger.info(f"Creating OpsGenie alert for incident {incident.jira_issue_key}")
        response = requests.post(url,json=payload,headers=headers)
        response.raise_for_status()
        return  {
            "data": response.json(),
            "status_code": response.status_code,
            "message": "Alert created successfully"
        }
    except RequestException as e:
        error_message = f"Failed to create alert: {str(e)}"
        logger.error(error_message)
        raise OpsGenieError(error_message) from e
              
       
   
   
   
