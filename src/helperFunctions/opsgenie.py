import requests
from config import settings

async def create_alert(incident):
    url = "https://api.opsgenie.com/v2/alerts"
    headers = {
        "Authorization": f"GenieKey {settings.opsgenie_api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "message": "Service Outage Alert",
        "description": f"An incident has been created with the following details: \n{incident}",
        "priority": "P1",
    }
    
    response = requests.post(url,json=payload,headers=headers)
    response.raise_for_status()
    return response.json()
       