from pydantic import BaseModel, Field, model_validator
from datetime import datetime
from pydantic import EmailStr
from typing import Optional

# #User related request model in pydantic

# class UserRequest(BaseModel):
#     email: EmailStr
#     password: str
#     team_id: str # Team ID of the Slack workspace where the user is sending the request
#     user_id: str # User ID of the user sending the request
#     user_name: str # User name of the user sending the request
#     token: str # Token used to authenticate the request

#     # @model_validator
#     # def validate_token(cls, values):
#     #     token = values.get('token')
#     #     slack_signature = values.get('HTTP_X_SLACK_SIGNATURE')
#     #     slack_request_timestamp = values.get('HTTP_X_SLACK_REQUEST_TIMESTAMP')
#     #     basestring = f"v0:{slack_request_timestamp}:{values.get('raw_body')}".encode('utf-8')
#     #     slack_signing_secret = settings.slack_signing_secret
#     #     slack_hash = 'v0=' + hmac.new(slack_signing_secret.encode('utf-8'), basestring, hashlib.sha256).hexdigest()
#     #     if not hmac.compare_digest(slack_hash, slack_signature):
#     #         raise ValueError("Invalid Slack request signature")
#         # return values

# #Response model
# class UserResponse(BaseModel):
#     id:int
#     email:EmailStr
#     created_at:datetime
#     class Config:
#         orm_mode = True

# How the response should look like for the request to create an incident


class Incident(BaseModel):
    """Model for creating and updating incidents."""

    affected_products: str = Field(..., min_length=3, max_length=20)
    severity: str = Field(..., min_length=3, max_length=20)
    suspected_owning_team: str = Field(..., min_length=3, max_length=20)
    start_time: datetime
    p1_customer_affected: bool
    suspected_affected_components: str = Field(..., min_length=3, max_length=20)
    description: str = Field(..., min_length=10, max_length=250)
    message_for_sp: Optional[str] = Field(None, min_length=0, max_length=250)
    statuspage_notification: bool = Field(False)
    separate_channel_creation: bool = Field(False)


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
