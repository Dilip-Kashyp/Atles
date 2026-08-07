import secrets
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import get_settings
from app.database.session import get_db
from app.auth.jwt import create_access_token, create_refresh_token, verify_token
from app.auth.oauth_registry import oauth_registry
from app.utils.redis import redis_client

from app.domain.identity.services import IdentityService, SessionService
from app.domain.workspace.services import WorkspaceService
from app.models.tenancy import User, Organization, Workspace, Membership

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


def resolve_redirect_uri(provider: str, redirect_uri: str | None) -> str:
    """Resolve the OAuth callback URL for the provider, using the configured backend callback by default."""
    defaults = {
        "github": settings.github_redirect_uri if hasattr(settings, "github_redirect_uri") else "http://localhost:8000/api/auth/github/callback",
        "google": settings.google_redirect_uri,
        "slack": settings.slack_redirect_uri,
    }
    default_redirect_uri = defaults.get(provider.lower(), f"http://localhost:8000/api/auth/{provider}/callback")

    if not redirect_uri:
        return default_redirect_uri

    return default_redirect_uri


@router.get("/{provider}/login")
async def login(provider: str, redirect_uri: str = None):
    """Initiate OAuth login flow for a user."""
    try:
        provider_impl = oauth_registry.get_provider(provider)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unsupported login provider: {provider}")

    state = secrets.token_urlsafe(32)
    # Store state in Redis for 10 minutes to verify on callback
    await redis_client.setex(f"oauth_state:{state}", 600, provider)

    resolved_redirect_uri = resolve_redirect_uri(provider, redirect_uri)
    auth_url = provider_impl.get_authorization_url(state, resolved_redirect_uri)
    return RedirectResponse(auth_url)


@router.get("/{provider}/callback")
async def callback(
    provider: str,
    code: str,
    state: str,
    redirect_uri: str | None = None,
    response: Response = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle OAuth redirect callback and authenticate the user."""
    # Verify OAuth state
    state_key = f"oauth_state:{state}"
    saved_provider = await redis_client.get(state_key)
    if not saved_provider or saved_provider != provider:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
    await redis_client.delete(state_key)

    try:
        provider_impl = oauth_registry.get_provider(provider)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unsupported login provider: {provider}")

    resolved_redirect_uri = resolve_redirect_uri(provider, redirect_uri)

    # Exchange authorization code for tokens and profile
    token_payload = await provider_impl.exchange_code(code, resolved_redirect_uri)
    user_info = token_payload.get("user_info", {})
    email = user_info.get("email")

    identity_service = IdentityService(db)
    session_service = SessionService(db)
    workspace_service = WorkspaceService(db)

    provider_user_id = str(token_payload.get("provider_user_id") or email)

    user, oauth_acc, is_new = await identity_service.find_or_create_user_from_oauth(
        provider=provider,
        provider_user_id=provider_user_id,
        provider_email=email,
        profile_data=token_payload,
        access_token=token_payload.get("access_token"),
        refresh_token=token_payload.get("refresh_token"),
    )

    if is_new:
        await workspace_service.provision_personal_workspace(user)

    # Generate Auth tokens & Session
    session, access_token, raw_refresh = await session_service.create_session(user_id=user.id)

    # Set refresh token as secure cookie
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/api",
    )

    frontend_origin = settings.frontend_origin.rstrip("/")
    frontend_redirect = f"{frontend_origin}{settings.frontend_redirect_path}#access_token={access_token}"
    return RedirectResponse(frontend_redirect, status_code=302)


@router.post("/refresh")
async def refresh(refresh_token: str = Cookie(None), response: Response = None):
    """Exchange a valid refresh token for a new access token."""
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    user_id = verify_token(refresh_token, expected_type="refresh")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    new_access_token = create_access_token(user_id)
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response):
    """Clear authorization cookies."""
    response.delete_cookie("refresh_token")
    return {"message": "Successfully logged out"}
