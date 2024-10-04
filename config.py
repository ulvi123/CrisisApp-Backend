import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NGROK_AUTHTOKEN: str
    SLACK_SIGNING_SECRET: str
    SLACK_VERIFICATION_TOKEN: str
    SLACK_BOT_TOKEN: str
    SLACK_GENERAL_OUTAGES_CHANNEL: str
    SLACK_CLIENT_ID: str
    SLACK_TOKEN_URL: str
    SLACK_CLIENT_SECRET: str
    SLACK_REDIRECT_URI: str
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    opsgenie_api_key: str
    jira_api_key: str
    jira_email: str
    jira_server: str

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        
        
print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")  

def get_settings() -> Settings:
    return Settings()
      
settings = get_settings()
