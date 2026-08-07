"""
BaseLoginProvider Abstract Interface.

Defines standard login provider capabilities separate from data integrations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseLoginProvider(ABC):
    """
    Plugin interface for identity/login assertion providers (Google, GitHub, Microsoft, Slack, Okta, SAML).
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Unique provider identifier (e.g. 'google', 'github', 'okta')."""
        pass

    @abstractmethod
    def get_authorization_url(
        self, state: str, redirect_uri: str, pkce_challenge: Optional[str] = None
    ) -> str:
        """Return the external authorization redirect URL."""
        pass

    @abstractmethod
    async def exchange_code(
        self, code: str, redirect_uri: str, pkce_verifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for tokens and standardized profile dictionary.

        Returned dictionary structure:
        {
            "provider_user_id": str,
            "email": str,
            "name": Optional[str],
            "username": Optional[str],
            "avatar_url": Optional[str],
            "access_token": Optional[str],
            "refresh_token": Optional[str],
            "expires_in": Optional[int],
            "scopes": List[str],
            "raw_profile": Dict[str, Any]
        }
        """
        pass
