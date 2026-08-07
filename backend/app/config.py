from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = "gemini-2.0-flash"
    slack_bot_token: str = ""
    slack_signing_secret: str = ""
    slack_bot_user_id: str = ""
    slack_timestamp_tolerance_seconds: int = 300
    slack_dedup_ttl_seconds: int = 600
    slack_dedup_fail_mode: str = "open"
    
    
    database_url: str = "postgresql+asyncpg://atlas:atlas_secure_pass@localhost:5432/atlas_dev"
    database_sync_url: str = "postgresql://atlas:atlas_secure_pass@localhost:5432/atlas_dev"
    redis_url: str = "redis://localhost:6379/0"
    
    
    atlas_master_key: str = "super_secret_master_key_change_me_32_bytes!"
    cookie_secure: bool = False
    
    
    github_client_id: str = ""
    github_client_secret: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/google/callback"

    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_redirect_uri: str = "http://localhost:8000/api/auth/slack/callback"

    frontend_origin: str = "http://localhost:3000"
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
