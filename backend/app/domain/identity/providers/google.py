"""
Google Login Provider Implementation.
"""
from typing import Any

import httpx

from app.config import get_settings
from app.constants import (
    GOOGLE_AUTHORIZE_URL,
    GOOGLE_TOKEN_URL,
    GOOGLE_USER_INFO_URL,
)
from app.domain.identity.providers.base import BaseLoginProvider


class GoogleLoginProvider(BaseLoginProvider):
    @property
    def provider_name(self) -> str:
        return "google"

    def get_authorization_url(
        self, state: str, redirect_uri: str, pkce_challenge: str | None = None
    ) -> str:
        settings = get_settings()
        client_id = settings.google_client_id
        scope = "openid email profile"
        url = (
            f"{GOOGLE_AUTHORIZE_URL}"
            f"?response_type=code&client_id={client_id}"
            f"&redirect_uri={redirect_uri}&scope={scope}&state={state}&prompt=consent&access_type=offline"
        )
        if pkce_challenge:
            url += f"&code_challenge={pkce_challenge}&code_challenge_method=S256"
        return url

    async def exchange_code(
        self, code: str, redirect_uri: str, pkce_verifier: str | None = None
    ) -> dict[str, Any]:
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            data = {
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            }
            if pkce_verifier:
                data["code_verifier"] = pkce_verifier

            resp = await client.post(GOOGLE_TOKEN_URL, data=data)
            if resp.status_code != 200:
                raise RuntimeError(f"Google token exchange failed: {resp.text}")

            token_data = resp.json()
            access_token = token_data.get("access_token")

            
            userinfo_resp = await client.get(
                GOOGLE_USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch Google user profile: {userinfo_resp.text}")

            profile = userinfo_resp.json()
            return {
                "provider_user_id": str(profile.get("sub")),
                "email": profile.get("email"),
                "name": profile.get("name"),
                "username": profile.get("email", "").split("@")[0] if profile.get("email") else None,
                "avatar_url": profile.get("picture"),
                "access_token": access_token,
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "scopes": token_data.get("scope", "").split(),
                "raw_profile": profile,
            }
