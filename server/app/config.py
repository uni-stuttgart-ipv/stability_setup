# filepath: app/config.py
from pydantic import BaseModel
from pydantic_settings import BaseSettings


class EmailConfigSettings(BaseSettings):
    """
    Pydantic model for SMTP server configuration.
    Reads settings from environment variables.
    """
    SMTP_HOST: str
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAILS_FROM_EMAIL: str
    EMAILS_FROM_NAME: str = "My Application"

    class Config:
        env_file = ".env"
        extra = "ignore"


# Instantiate the settings
email_settings = EmailConfigSettings()
