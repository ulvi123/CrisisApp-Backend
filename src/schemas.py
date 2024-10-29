from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional,List


class IncidentBase(BaseModel):
    """Base model for incident."""
    affected_products: List[str]
    so_number:str = Field(..., description="SO Number")
    severity: List[str]
    suspected_owning_team: List[str]
    start_time: datetime
    end_time: datetime
    p1_customer_affected: bool
    suspected_affected_components: List[str]
    description: str
    message_for_sp: Optional[str] = Field(None, min_length=0, max_length=250)
    statuspage_notification: bool = Field(False)
    separate_channel_creation: bool = Field(False)
    jira_issue_key: str = None

class IncidentCreate(IncidentBase):
    """Model for creating an incident."""
    pass


class IncidentResponse(IncidentBase):
    """Response model for incident."""
    id: int
    created_at: datetime

    class Config:
        orm_mode = True
        
class IncidentOut(BaseModel):
    Incident: IncidentResponse



class IncidenUpdate(BaseModel):
    status: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, min_length=0, max_length=250)
    severity: Optional[List[str]] = Field(None)