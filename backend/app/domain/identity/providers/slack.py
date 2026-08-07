"""
Slack Login Provider Implementation.
"""
from typing import Any, Dict, Optional
import httpx
from app.config import get_settings
from app.domain.identity.providers.base import BaseLoginProvider


class SlackLoginProvider(BaseLoginProvider):
    @property
    def provider_name(self) -> str:
        return "slack"

    def get_authorization_url(
        self, state: str, redirect_uri: str, pkce_challenge: Optional[str] = None
    ) -> str:
        settings = get_settings()
        client_id = settings.slack_client_id
        # Scopes required for identity and bot tasks
        user_scope = "identity.basic,identity.email,identity.avatar"
        bot_scope = "chat:write,commands,channels:read"
        
        url = (
            "https://slack.com/oauth/v2/authorize"
            f"?client_id={client_id}&redirect_uri={redirect_uri}&state={state}"
            f"&user_scope={user_scope}&scope={bot_scope}"
        )
        return url

    async def exchange_code(
        self, code: str, redirect_uri: str, pkce_verifier: Optional[str] = None
    ) -> Dict[str, Any]:
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://slack.com/api/oauth.v2.access",
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

            # For Slack v2, we get an authed_user object for the user who installed it
            authed_user = token_data.get("authed_user", {})
            user_id = authed_user.get("id")
            access_token = authed_user.get("access_token") # User token
            bot_token = token_data.get("access_token") # Bot token

            # Fetch user profile using user token
            user_resp = await client.get(
                "https://slack.com/api/users.identity",
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
                "access_token": bot_token or access_token,  # Default to bot token for workspace tasks
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "scopes": token_data.get("scope", "").split(","),
                "raw_profile": token_data,
            }
