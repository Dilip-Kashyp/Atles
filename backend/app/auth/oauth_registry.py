import httpx
from abc import ABC, abstractmethod
from typing import Dict, Any
from app.config import get_settings

settings = get_settings()


class BaseOAuthProvider(ABC):
    @abstractmethod
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Generate the authorization URL to redirect the user to."""
        pass

    @abstractmethod
    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange the code for tokens and fetch user profile details."""
        pass


class GitHubOAuthProvider(BaseOAuthProvider):
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        client_id = settings.github_client_id
        return (
            f"https://github.com/login/oauth/authorize"
            f"?client_id={client_id}"
            f"&state={state}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=read:user,user:email,repo"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            # Exchange code for access token
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError(f"GitHub OAuth error: {token_data.get('error_description', 'No access token returned')}")

            # Get user info
            user_resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()

            # GitHub users can have hidden emails. Retrieve primary email if missing.
            email = user_data.get("email")
            if not email:
                emails_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if emails_resp.status_code == 200:
                    for em in emails_resp.json():
                        if em.get("primary") and em.get("verified"):
                            email = em.get("email")
                            break

            return {
                "access_token": access_token,
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "user_info": {
                    "email": email or f"{user_data.get('login')}@github.com",
                    "name": user_data.get("name") or user_data.get("login"),
                    "avatar_url": user_data.get("avatar_url"),
                },
            }


class GoogleOAuthProvider(BaseOAuthProvider):
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        client_id = settings.google_client_id
        return (
            "https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}"
            f"&state={state}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope=openid%20email%20profile"
            f"&access_type=offline"
            f"&prompt=select_account"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("Google OAuth error: no access token returned")

            user_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()

            return {
                "access_token": access_token,
                "refresh_token": token_data.get("refresh_token"),
                "expires_in": token_data.get("expires_in"),
                "user_info": {
                    "email": user_data.get("email"),
                    "name": user_data.get("name") or user_data.get("given_name"),
                    "avatar_url": user_data.get("picture"),
                },
            }


class SlackOAuthProvider(BaseOAuthProvider):
    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        client_id = settings.slack_client_id
        # Request slack user profile scopes and bot installation scopes
        return (
            f"https://slack.com/oauth/v2/authorize"
            f"?client_id={client_id}"
            f"&state={state}"
            f"&redirect_uri={redirect_uri}"
            f"&scope=incoming-webhook,commands,chat:write"
            f"&user_scope=identity.basic,identity.email,identity.avatar"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": settings.slack_client_id,
                    "client_secret": settings.slack_client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            if not token_data.get("ok"):
                raise ValueError(f"Slack OAuth error: {token_data.get('error')}")

            # Extract authed user details
            authed_user = token_data.get("authed_user", {})
            user_token = authed_user.get("access_token")

            # Fetch user identity
            user_info = {}
            if user_token:
                identity_resp = await client.get(
                    "https://slack.com/api/users.identity",
                    headers={"Authorization": f"Bearer {user_token}"},
                )
                identity_data = identity_resp.json()
                if identity_data.get("ok"):
                    user_info = {
                        "email": identity_data.get("user", {}).get("email"),
                        "name": identity_data.get("user", {}).get("name"),
                        "avatar_url": identity_data.get("user", {}).get("image_512"),
                    }

            return {
                "access_token": token_data.get("access_token"),  # Bot Token
                "user_access_token": user_token,  # User Token (if needed)
                "team_id": token_data.get("team", {}).get("id"),
                "team_name": token_data.get("team", {}).get("name"),
                "user_info": user_info or {
                    "email": f"{authed_user.get('id')}@slack.com",
                    "name": authed_user.get("id"),
                    "avatar_url": None,
                },
            }


class OAuthRegistry:
    def __init__(self):
        self._providers: Dict[str, BaseOAuthProvider] = {
            "github": GitHubOAuthProvider(),
            "google": GoogleOAuthProvider(),
            "slack": SlackOAuthProvider(),
        }

    def get_provider(self, name: str) -> BaseOAuthProvider:
        provider = self._providers.get(name.lower())
        if not provider:
            raise KeyError(f"OAuth Provider '{name}' is not registered.")
        return provider


# Global Registry Instance
oauth_registry = OAuthRegistry()
