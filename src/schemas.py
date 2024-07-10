from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from pydantic import EmailStr
from typing import Optional



# class Incident(BaseModel):
#     """Model for creating and updating incidents."""
#     affected_products: str = Field(..., min_length=3, max_length=20)
#     severity: str = Field(..., min_length=3, max_length=20)
#     suspected_owning_team: str = Field(..., min_length=3, max_length=20)
#     start_time: datetime
#     p1_customer_affected: bool
#     suspected_affected_components: str = Field(..., min_length=3, max_length=20)
#     description: str = Field(..., min_length=10, max_length=250)
#     message_for_sp: Optional[str] = Field(None, min_length=0, max_length=250)
#     statuspage_notification: bool = Field(False)
#     separate_channel_creation: bool = Field(False)


class Incident(BaseModel):
    """Model for creating and updating incidents."""
    affected_products: str = Field(..., min_length=3, max_length=50)
    severity: str = Field(..., min_length=3, max_length=50)
    suspected_owning_team: str = Field(..., min_length=3, max_length=50)
    start_time: datetime
    end_time: datetime
    p1_customer_affected: bool
    suspected_affected_components: str = Field(..., min_length=3, max_length=50)
    description: str = Field(..., min_length=10, max_length=250)
    message_for_sp: Optional[str] = Field(None, min_length=0, max_length=250)
    statuspage_notification: bool = Field(False)
    separate_channel_creation: bool = Field(False)
    status: Optional[str] = Field(None, max_length=50)


class IncidentBase(BaseModel):
    """Base model for incident."""

    affected_products: str
    severity: str
    suspected_owning_team: str
    start_time: datetime
    p1_customer_affected: bool
    suspected_affected_components: str
    description: str
    message_for_sp: str
    statuspage_notification: bool = Field(False)
    separate_channel_creation: bool = Field(False)


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
