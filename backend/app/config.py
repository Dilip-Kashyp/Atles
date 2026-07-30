from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str
    gemini_model: str = ""
    slack_bot_token: str
    slack_signing_secret: str = ""
    slack_bot_user_id: str = ""
    mcp_server_script: str = "../mcp-servers/slack/server.py"
    github_mcp_server_script: str = "../mcp-servers/github/server.py"
    notion_mcp_server_script: str = "../mcp-servers/notion/server.py"
    github_token: str = ""
    notion_token: str = ""

    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
