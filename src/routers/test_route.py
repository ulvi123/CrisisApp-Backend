# from fastapi import APIRouter, Body, Depends, HTTPException, Query
# from sqlalchemy.orm import Session
# from enum import Enum
# from datetime import datetime
# from src.database import get_db
# from src.middleware import require_role
# from src.models import UserRole, UserToken, Base
# from pydantic import BaseModel

# router = APIRouter(
#     prefix="/test",
#     tags=["Test"]
# )


# class CreateUserRequest(BaseModel):
#     user_id:str
#     token: str
#     role:UserRole = UserRole.USER

# class UserRole(str,Enum):
#     USER = "USER"
#     SUPPORT = "SUPPORT"



# @router.post('/create-user')
# async def create_user(
#     request:CreateUserRequest,
#     db: Session = Depends(get_db)
# ):
#     new_user = UserToken(
#         user_id = request.user_id,
#         encrypted_token = request.token,
#         role=request.role,
#         created_at = datetime.now()
#     )
    
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)
#     return {"messsage": f"User is created with role: {new_user.role}"}



# @router.post("/incidents")
# async def test_create_incident(
#     incident_data: dict = None,
#     user: UserToken = Depends(require_role(UserRole.SUPPORT))  # Use require_role properly
# ):
#     return {
#         "message": "Incident created",
#         "user_id": user.user_id,
#         "role": user.role,
#         "incident_data": incident_data
#     }

# @router.get("/test/incidents")
# async def test_view_incidents(
#     db:Session = Depends(get_db),
#     user_id: str = Query(...,description="The slack user id"),
# ):
    
#     user  = await require_role(user_idrequired_role = UserRole.USER, db = db)
#     return {
#         "message": "Incidents retrieved",
#         "user_id": user.user_id,
#         "role": user.role
#     }