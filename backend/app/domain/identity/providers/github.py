"""
GitHub Login Provider Implementation.
"""
from typing import Any

import httpx

from app.config import get_settings
from app.constants import (
    GITHUB_ACCESS_TOKEN_URL,
    GITHUB_AUTHORIZE_URL,
    GITHUB_USER_EMAILS_URL,
    GITHUB_USER_INFO_URL,
)
from app.domain.identity.providers.base import BaseLoginProvider


class GithubLoginProvider(BaseLoginProvider):
    @property
    def provider_name(self) -> str:
        return "github"

    def get_authorization_url(
        self, state: str, redirect_uri: str, pkce_challenge: str | None = None
    ) -> str:
        settings = get_settings()
        client_id = settings.github_client_id
        scope = "read:user user:email"
        url = (
            f"{GITHUB_AUTHORIZE_URL}"
            f"?client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={state}"
        )
        return url

    async def exchange_code(
        self, code: str, redirect_uri: str, pkce_verifier: str | None = None
    ) -> dict[str, Any]:
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                GITHUB_ACCESS_TOKEN_URL,
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200:
                raise RuntimeError(f"GitHub token exchange failed: {resp.text}")

            token_data = resp.json()
            access_token = token_data.get("access_token")

            
            user_resp = await client.get(
                GITHUB_USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}", "User-Agent": "Atlas-SaaS"},
            )
            if user_resp.status_code != 200:
                raise RuntimeError(f"Failed to fetch GitHub user profile: {user_resp.text}")
            profile = user_resp.json()

            
            email = profile.get("email")
            if not email:
                emails_resp = await client.get(
                    GITHUB_USER_EMAILS_URL,
                    headers={"Authorization": f"Bearer {access_token}", "User-Agent": "Atlas-SaaS"},
                )
                if emails_resp.status_code == 200:
                    emails = emails_resp.json()
                    primary_email = next((e["email"] for e in emails if e.get("primary")), None)
                    email = primary_email or (emails[0]["email"] if emails else None)

            return {
                "provider_user_id": str(profile.get("id")),
                "email": email,
                "name": profile.get("name") or profile.get("login"),
                "username": profile.get("login"),
                "avatar_url": profile.get("avatar_url"),
                "access_token": access_token,
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "scopes": token_data.get("scope", "").split(","),
                "raw_profile": profile,
            }
