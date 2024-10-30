from typing import Any, Dict, Optional
from fastapi import HTTPException,status
from pydantic import BaseModel
import requests
import logging
from sqlalchemy.orm import Session
from fastapi import Depends
from config import get_settings, Settings
from src import models
from src.database import get_db
import httpx


settings = get_settings()

class StatusResponse(BaseModel):
    incident_id:str
    issue_key:str
    
class StatuspageStatusUpdate(BaseModel):
    incident_id: str
    new_status: str
    additional_info: Optional[str] = ""

#Create statuspage incident
async def create_statuspage_incident(incident_data,settings,db: Session = Depends(get_db)):
    headers = {
        "Authorization": f"Bearer {settings.statuspage_api_key}",
        "Content-Type":"application/json",
    } 
    
    incident_dict = {
        "id": incident_data.id,
        "so_number": incident_data.so_number,
        "affected_products": incident_data.affected_products or [],  # Handle possible None
        "severity": incident_data.severity or [],  # Handle possible None
        "suspected_owning_team": incident_data.suspected_owning_team or [],
        "start_time": incident_data.start_time.isoformat() if incident_data.start_time else None,
        "end_time": incident_data.end_time.isoformat() if incident_data.end_time else None,
        "p1_customer_affected": incident_data.p1_customer_affected,
        "suspected_affected_components": incident_data.suspected_affected_components or [],
        "description": incident_data.description or "No description provided",
        "message_for_sp": incident_data.message_for_sp,
        "statuspage_notification": incident_data.statuspage_notification,
        "status": incident_data.status
    }
    
    
    #improved payload formatting
    incident_payload = {
        "incident": {
            "name": f"🚨 Incident Report: {incident_dict['so_number']} 🚨",
            "status": "investigating",
            "body": (
                f"*Incident Summary:*\n"
                f"----------------------------------\n"
                f"🔹 *SO Number:* {incident_dict['so_number']}\n"
                f"🔹 *Severity Level:* {', '.join(incident_dict['severity'])}\n"
                f"🔹 *Affected Products:* {', '.join(incident_dict['affected_products'])}\n"
                f"🔹 *Suspected Teams:* {', '.join(incident_dict['suspected_owning_team'])}\n"
                f"🔹 *Start Time:* {incident_dict['start_time']}\n"
                f"🔹 *Affected Components:* {', '.join(incident_dict['suspected_affected_components'])}\n"
                f"\n"
                f"*Additional Details:*\n"
                f"----------------------------------\n"
                f"📝 *Description:* {incident_dict['description']}\n"
                f"📢 *Message:* {incident_dict['message_for_sp'] or 'No additional message'}\n"
                f"👥 *Customer Affected:* {'Yes' if incident_dict['p1_customer_affected'] else 'No'}"
            ),
            "components": {
                settings.statuspage_component_id: "degraded_performance"
            },
            "component_ids": [settings.statuspage_component_id],
            "deliver_notifications": True,
        }
    }
    
    
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.statuspage_url}/{settings.statuspage_page_id}/incidents",
                headers=headers,
                json=incident_payload,
                timeout=10
            )
            
        # Log the response for debugging
        logging.info(f"Statuspage response: {response.status_code} - {response.text}")
        response_data = response.json()
        
        
        simplified_response = {
            "incident_id": incident_data.id,
            "issue_key": incident_data.so_number
        }
        
        if response.status_code not in (200, 201) or not response_data.get("id"):
            logging.error(f"Failed to create statuspage incident: Status {response.status_code} - {response_data}")
            raise HTTPException(status_code=500, detail=f"Failed to create statuspage incident: {response_data}")
        
    
        #Saving the incident ID for future reference to update the incident status in the statuspage
        if response_data.get('id'):
            incident_data.statuspage_incident_id = response_data['id']
            db.commit()
            db.refresh(incident_data)
        
        logging.info(f"Statuspage incident created: {response_data}")
        return StatusResponse(**simplified_response).dict()
    
    except httpx.RequestError as e:
        logging.error(f"Network error creating statuspage incident: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        logging.error(f"Failed to create statuspage incident: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    
    
#Update statuspage incident status   
async def update_statuspage_incident_status(
    db_incident, 
    new_status: str,
    settings,
    additional_info: str = ""
) -> Dict[str, Any]:
    
    if not db_incident.statuspage_incident_id:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST, 
          detail="No statuspage incident ID found in the database."
    )
      
    valid_statuses = {
        "investigating", 
        "identified", 
        "monitoring", 
        "resolved"
    }
    if new_status.lower() not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    headers = {
        "Authorization": f"Bearer {settings.statuspage_api_key}",
        "Content-Type":"application/json",
    }
    
    # Format the body as a string
    update_body = (
        f"Status updated to '{new_status.capitalize()}'.\n\n"
        f"{additional_info if additional_info else 'No additional information provided.'}"
    )
    
    update_payload = {
        "incident":{
            "id":db_incident.statuspage_incident_id,
            "status":new_status.lower(),
            "body":update_body,
            "components":{
                settings.statuspage_component_id: "operational" if new_status.lower() == "resolved" else "degraded_performance"
            }
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{settings.statuspage_url}/{settings.statuspage_page_id}/incidents/{db_incident.statuspage_incident_id}",
                headers=headers,
                json=update_payload,
                timeout=10
            )
        if response.status_code != 200:
            error_message = f"Failed to update statuspage incident: Status {response.status_code}"
            try:
                error_data = response.json()
                error_message += f" - {error_data}"
            except ValueError:
                error_message += f" - {response.text}"
            
            logging.error(error_message)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update statuspage incident"
            )
        
        response_data = response.json()
        logging.info(f"Statuspage incident updated: {response_data}")
        return response_data
    
    except httpx.RequestError as e:
        error_message = f"Network error updating statuspage incident: {str(e)}"
        logging.error(error_message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )
    except Exception as e:
        error_message = f"Unexpected error updating statuspage incident: {str(e)}"
        logging.error(error_message)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message
        )
      
      
    
    
 
    
    


