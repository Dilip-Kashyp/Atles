from functools import lru_cache

from app.constants import (
    DEFAULT_API_REDIRECT_URI_TEMPLATE,
    DEFAULT_API_V1_REDIRECT_URI_TEMPLATE,
    DEFAULT_DATABASE_SYNC_URL,
    DEFAULT_DATABASE_URL,
    DEFAULT_FRONTEND_ORIGIN,
    DEFAULT_REDIS_URL,
)

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = ""
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_bot_user_id: str = ""
    slack_timestamp_tolerance_seconds: int = 300
    slack_dedup_ttl_seconds: int = 600
    slack_dedup_fail_mode: str = "open"
    
    
    database_url: str = DEFAULT_DATABASE_URL
    database_sync_url: str = DEFAULT_DATABASE_SYNC_URL
    redis_url: str = DEFAULT_REDIS_URL
    
    
    atlas_master_key: str = "super_secret_master_key_change_me_32_bytes!"
    cookie_secure: bool = False
    
    
    github_client_id: str = ""
    github_client_secret: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = DEFAULT_API_V1_REDIRECT_URI_TEMPLATE.format(provider="google")

    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_redirect_uri: str = DEFAULT_API_V1_REDIRECT_URI_TEMPLATE.format(provider="slack")

    frontend_origin: str = DEFAULT_FRONTEND_ORIGIN
    frontend_redirect_path: str = "/"

    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
