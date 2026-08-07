"""Login Provider Plugins Package."""
from app.domain.identity.providers.base import BaseLoginProvider
from app.domain.identity.providers.github import GithubLoginProvider
from app.domain.identity.providers.google import GoogleLoginProvider
from app.domain.identity.providers.registry import login_provider_registry
from app.domain.identity.providers.slack import SlackLoginProvider

login_provider_registry.register(GoogleLoginProvider())
login_provider_registry.register(GithubLoginProvider())
login_provider_registry.register(SlackLoginProvider())

__all__ = [
    "BaseLoginProvider",
    "GithubLoginProvider",
    "GoogleLoginProvider",
    "SlackLoginProvider",
    "login_provider_registry",
]
