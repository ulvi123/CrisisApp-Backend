from fastapi import HTTPException
import requests
import logging



async def create_statuspage_incident(incident_data,settings):
    headers = {
        "Authorization": f"Bearer {settings.statuspage_api_key}",
        "Content-Type":"application/json",
    }
    
    #the payload
    # Create the incident_payload using the incident_data
    incident_payload = {
            "incident": {
                "name": f"Incident: {incident_data.get('so_number')}",
                "status": "investigating",
                "body": f"An incident has been reported for SO Number: {incident_data.get('so_number')}. "
                        f"Severity: {', '.join(incident_data.get('severity', [])) if incident_data.get('severity') else 'None'}. "
                        f"Affected Products: {', '.join(incident_data.get('affected_products', [])) if incident_data.get('affected_products') else 'None'}. "
                        f"Description: {incident_data.get('description', 'No description provided')}. "
                        f"Customer Affected: {'Yes' if incident_data.get('p1_customer_affected') else 'No'}.",
                "components": {
                    settings.statuspage_component_id: "degraded_performance"  # Assuming the status I want to set for this component
                },
                "component_ids": [settings.statuspage_component_id],  # IDs of components affected
                "deliver_notifications": True,  # Whether to send notifications for this incident
            }
        }


    
    try:
        response = requests.post(
            f"{settings.statuspage_url}/{settings.statuspage_page_id}/incidents",
            json=incident_payload,
            headers=headers
        )
        response_data = response.json()
        
        if response.status_code != 200 or not response_data.get("id"):
            logging.error(f"Failed to create statuspage incident: {response_data}")
            raise HTTPException(status_code=500, detail="Failed to create statuspage incident")
        
        logging.info(f"Statuspage incident created: {response_data}")
        return response_data
    except Exception as e:
        logging.error(f"Failed to create statuspage incident: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create statuspage incident")