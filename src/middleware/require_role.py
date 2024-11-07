# from fastapi import FastAPI, HTTPException, Depends,status
# from sqlalchemy.orm import Session
# from src import models
# from src.database import get_db
# from enum import Enum
# from src.models import UserToken,UserRole


# class UserRole(str,Enum):
#     USER = "USER"
#     SUPPORT = "SUPPORT"


# async def require_role(required_role: UserRole):
#     async def role_checker(
#         user_id: str,  # This value will be injected from the request
#         db: Session = Depends(get_db)
#     ) -> UserToken:
#         # Getting the user from the UserToken table in the database
#         user = db.query(UserToken).filter(UserToken.user_id == user_id).first()

#         if not user:
#             raise HTTPException(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 detail="User not found. Please install the app first."
#             )

#         # Check if the user has the required role
#         if user.role != required_role:
#             raise HTTPException(
#                 status_code=status.HTTP_403_FORBIDDEN,
#                 detail="Access denied. You don't have the required role to perform this action."
#             )

#         return user

#     return role_checker