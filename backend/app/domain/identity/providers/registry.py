"""
LoginProviderRegistry.

Registry singleton for managing login assertion providers.
"""

from app.domain.identity.providers.base import BaseLoginProvider


class LoginProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, BaseLoginProvider] = {}

    def register(self, provider: BaseLoginProvider) -> None:
        self._providers[provider.provider_name.lower()] = provider

    def get(self, name: str) -> BaseLoginProvider:
        key = name.lower()
        if key not in self._providers:
            raise KeyError(f"Login provider '{name}' is not registered.")
        return self._providers[key]

    def is_supported(self, name: str) -> bool:
        return name.lower() in self._providers



login_provider_registry = LoginProviderRegistry()
