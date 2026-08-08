"""
Slack Login Provider Implementation.
"""
from typing import Any

import httpx

from app.config import get_settings
from app.constants import (
    SLACK_ACCESS_TOKEN_URL,
    SLACK_AUTHORIZE_URL,
    SLACK_USER_IDENTITY_URL,
)
from app.domain.identity.providers.base import BaseLoginProvider


class SlackLoginProvider(BaseLoginProvider):
    @property
    def provider_name(self) -> str:
        return "slack"

    def get_authorization_url(
        self, state: str, redirect_uri: str, pkce_challenge: str | None = None
    ) -> str:
        settings = get_settings()
        client_id = settings.slack_client_id
        
        user_scope = "identity.basic,identity.email,identity.avatar"
        bot_scope = "chat:write,commands,channels:read,users:read"
        
        url = (
            f"{SLACK_AUTHORIZE_URL}"
            f"?client_id={client_id}&redirect_uri={redirect_uri}&state={state}"
            f"&user_scope={user_scope}&scope={bot_scope}"
        )
        return url

    async def exchange_code(
        self, code: str, redirect_uri: str, pkce_verifier: str | None = None
    ) -> dict[str, Any]:
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SLACK_ACCESS_TOKEN_URL,
                data={
                    "client_id": settings.slack_client_id,
                    "client_secret": settings.slack_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Slack token exchange failed HTTP {resp.status_code}: {resp.text}")

            token_data = resp.json()
            if not token_data.get("ok"):
                raise RuntimeError(f"Slack token exchange failed: {token_data.get('error')}")

            
            authed_user = token_data.get("authed_user", {})
            user_id = authed_user.get("id")
            access_token = authed_user.get("access_token") 
            bot_token = token_data.get("access_token") 

            
            user_resp = await client.get(
                SLACK_USER_IDENTITY_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            profile_data = user_resp.json()
            if not profile_data.get("ok"):
                raise RuntimeError(f"Failed to fetch Slack user profile: {profile_data.get('error')}")

            user_info = profile_data.get("user", {})

            return {
                "provider_user_id": user_id,
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "username": user_info.get("name"),
                "avatar_url": user_info.get("image_512") or user_info.get("image_192"),
                "access_token": bot_token or access_token,  
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "scopes": token_data.get("scope", "").split(","),
                "raw_profile": token_data,
            }
