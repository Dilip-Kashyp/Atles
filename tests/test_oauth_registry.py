from app.api.auth import resolve_redirect_uri
from app.auth.oauth_registry import oauth_registry


def test_google_provider_is_registered_and_builds_authorization_url():
    provider = oauth_registry.get_provider("google")
    auth_url = provider.get_authorization_url("abc123", "http://localhost:8000/api/auth/google/callback")

    assert "accounts.google.com" in auth_url
    assert "client_id=" in auth_url
    assert "scope=openid%20email%20profile" in auth_url


def test_resolve_redirect_uri_falls_back_to_provider_default():
    assert resolve_redirect_uri("google", None) == "http://localhost:8000/api/auth/google/callback"
