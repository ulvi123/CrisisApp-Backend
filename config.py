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
    ENCRYPTION_KEY: str
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
    statuspage_api_key: str
    statuspage_page_id: str
    statuspage_component_id: str
    statuspage_url: str

    class Config:
        env_file = ".env"
        # case_sensitive = True
        env_file_encoding = 'utf-8'
        
        
print(f"Current working directory: {os.getcwd()}")
print(f".env file exists: {os.path.exists('.env')}")  

def get_settings() -> Settings:
    return Settings()
      
settings = get_settings()
