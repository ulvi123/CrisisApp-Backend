import os
from fastapi import FastAPI, Request,Depends
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse, RedirectResponse
from src.routers import incident  # type: ignore
from src.utils import initialize_options
from src.helperFunctions.slack_utils import test_slack_integration
from config import get_settings, Settings
import os
import logging
from fastapi.logger import logger as fastapi_logger
import httpx
from src.models import UserToken
from src.database import get_db
from src.utils import encrypt_token
from .database import get_db,SessionLocal
from cryptography.fernet import Fernet


app = FastAPI()
app.include_router(incident.router)

settings = get_settings()
encryption_key= settings.ENCRYPTION_KEY
cipher = Fernet(encryption_key.encode())



@app.on_event("startup")
async def startup_event():
    await initialize_options()


# @app.get("/")
# def root():
#     return {"message": "Hello World"}


if __name__ == "__main__":
    import asyncio

    asyncio.run(startup_event())
    asyncio.run(test_slack_integration())

"""
Below Code was used for testing purposes but still is kept for future debugging purposes
"""

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


#Slack authorization verification logic

@app.get("/slack/login")
async def slack_login():
    slack_auth_url = (
        f"https://slack.com/oauth/v2/authorize?client_id={settings.SLACK_CLIENT_ID}"
        f"&scope=users:read&redirect_uri={settings.SLACK_REDIRECT_URI}"
    )
    
    return RedirectResponse(slack_auth_url)

@app.get("/slack/oauth/callback")
async def slack_oauth_callback(request:Request, db:Session=Depends(get_db)):
    code = request.query_params.get("code")
    logging.info(f"Authorization code received: {code}")
    
    if not code:
        return {"error": "No authorization code received"}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.SLACK_TOKEN_URL,
            data = {
                "client_id": settings.SLACK_CLIENT_ID,
                "client_secret": settings.SLACK_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.SLACK_REDIRECT_URI
            }
        )
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if access_token:
            encrypted_token = cipher.encrypt(access_token.encode()).decode()
            
            #save to db
            db_token = UserToken(user_id="U123",encrypted_token=encrypted_token)
            db.add(db_token)
            db.commit()
            return {"message": "Authentication successful",access_token:access_token}
        
        return {"error": "Failed to retrieve access token"}