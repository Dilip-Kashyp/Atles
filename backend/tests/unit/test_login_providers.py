"""Unit tests for Login Provider plugins and registry."""
import pytest
from app.domain.identity.providers import login_provider_registry, GoogleLoginProvider, GithubLoginProvider


def test_login_provider_registry():
    assert login_provider_registry.is_supported("google") is True
    assert login_provider_registry.is_supported("github") is True
    assert login_provider_registry.is_supported("unsupported_provider") is False

    google_provider = login_provider_registry.get("google")
    assert isinstance(google_provider, GoogleLoginProvider)
    assert google_provider.provider_name == "google"

    github_provider = login_provider_registry.get("github")
    assert isinstance(github_provider, GithubLoginProvider)
    assert github_provider.provider_name == "github"


def test_google_provider_authorization_url():
    provider = GoogleLoginProvider()
    url = provider.get_authorization_url(state="test_state_123", redirect_uri="http://localhost/callback")
    assert "accounts.google.com" in url
    assert "state=test_state_123" in url
    assert "redirect_uri=http://localhost/callback" in url or "redirect_uri=http%3A%2F%2Flocalhost%2Fcallback" in url
