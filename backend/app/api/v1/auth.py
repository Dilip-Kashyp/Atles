"""
API v1 Auth Endpoints.

Handles OAuth login, account linking, account unlinking, account merging, session management, token refresh, and request context inspection.
"""
import secrets
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.context import CurrentIdentity
from app.database.session import get_db
from app.dependencies import get_current_identity, get_current_user
from app.domain.identity.providers import login_provider_registry
from app.domain.identity.schemas import (
    AccountMergeRequest,
    CurrentIdentityResponse,
    OAuthAccountResponse,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.domain.identity.services import (
    AccountLinkingService,
    IdentityService,
    MergeAccountService,
    SessionService,
)
from app.domain.shared.exceptions import AtlasError, AuthenticationError
from app.domain.workspace.services import WorkspaceService
from app.infrastructure.cache.redis import redis_client

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _resolve_redirect_uri(provider: str) -> str:
    defaults = {
        "google": settings.google_redirect_uri or "http://localhost:8000/api/v1/auth/google/callback",
        "github": getattr(settings, "github_redirect_uri", "http://localhost:8000/api/v1/auth/github/callback"),
        "slack": settings.slack_redirect_uri or "http://localhost:8000/api/v1/auth/slack/callback",
    }
    return defaults.get(provider.lower(), f"http://localhost:8000/api/v1/auth/{provider}/callback")


@router.get("/{provider}/login")
@router.post("/{provider}/login")
async def login(provider: str, request: Request):
    if not login_provider_registry.is_supported(provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported login provider: '{provider}'",
        )

    provider_impl = login_provider_registry.get(provider)
    state = secrets.token_urlsafe(32)

    auth_header = request.headers.get("Authorization")
    user_id = None
    if auth_header and auth_header.startswith("Bearer "):
        from app.infrastructure.security.tokens import verify_access_token
        payload = verify_access_token(auth_header[7:])
        if payload:
            user_id = payload.get("sub")

    state_val = f"{provider}:{user_id}" if user_id else provider
    await redis_client.setex(f"oauth_state:{state}", 600, state_val)

    redirect_uri = _resolve_redirect_uri(provider)
    auth_url = provider_impl.get_authorization_url(state, redirect_uri)
    return RedirectResponse(auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/{provider}/callback")
async def callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    state_key = f"oauth_state:{state}"
    saved_state = await redis_client.get(state_key)
    if not saved_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter.",
        )
    await redis_client.delete(state_key)

    state_parts = saved_state.split(":")
    saved_provider = state_parts[0]
    linking_user_id = state_parts[1] if len(state_parts) > 1 else None

    if saved_provider != provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider mismatch in OAuth state.",
        )

    if not login_provider_registry.is_supported(provider):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    provider_impl = login_provider_registry.get(provider)
    redirect_uri = _resolve_redirect_uri(provider)
    token_payload = await provider_impl.exchange_code(code, redirect_uri)
    email = token_payload.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="OAuth provider did not return user email.")

    identity_service = IdentityService(db)
    session_service = SessionService(db)
    workspace_service = WorkspaceService(db)
    linking_service = AccountLinkingService(db)

    provider_user_id = str(token_payload.get("provider_user_id"))

    if linking_user_id:
        from uuid import UUID
        user = await identity_service.get_user_by_id(UUID(linking_user_id))
        await linking_service.link_provider(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
            profile_data=token_payload,
            access_token=token_payload.get("access_token"),
            refresh_token=token_payload.get("refresh_token"),
        )
    else:
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

    ip_addr = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")

    session, access_token, raw_refresh_token = await session_service.create_session(
        user_id=user.id,
        ip_address=ip_addr,
        user_agent=user_agent,
    )

    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/api/v1/auth",
    )

    frontend_origin = settings.frontend_origin.rstrip("/")
    frontend_redirect = f"{frontend_origin}{settings.frontend_redirect_path}#access_token={access_token}"
    return RedirectResponse(frontend_redirect, status_code=status.HTTP_302_FOUND)


@router.post("/link/{provider}", response_model=OAuthAccountResponse)
async def link_provider(
    provider: str,
    request: Request,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not login_provider_registry.is_supported(provider):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    return await login(provider, request)


@router.delete("/unlink/{provider}")
async def unlink_provider(
    provider: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    linking_service = AccountLinkingService(db)
    try:
        await linking_service.unlink_provider(current_user.id, provider)
    except AtlasError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
    return {"message": f"Successfully unlinked {provider} account."}


@router.post("/merge", response_model=UserResponse)
async def merge_accounts(
    payload: AccountMergeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    merge_service = MergeAccountService(db)
    try:
        merged_user = await merge_service.merge_accounts(
            primary_user_id=current_user.id,
            secondary_user_id=payload.secondary_user_id,
            actor_user_id=current_user.id,
        )
    except AtlasError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
    return UserResponse.model_validate(merged_user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    payload: Optional[RefreshRequest] = None,
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(get_db),
):
    raw_token = (payload.refresh_token if payload and payload.refresh_token else None) or refresh_token_cookie

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing from request.",
        )

    session_service = SessionService(db)
    try:
        new_access, new_refresh, user_id = await session_service.rotate_refresh_token(raw_token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    response = Response()
    response.set_cookie(
        key="refresh_token",
        value=new_refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/api/v1/auth",
    )
    return TokenResponse(access_token=new_access, token_type="bearer", expires_in=900)


@router.post("/logout")
async def logout(
    response: Response,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return {"message": "Successfully logged out."}


@router.post("/logout-all")
async def logout_all(
    response: Response,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session_service = SessionService(db)
    await session_service.logout_all_sessions(current_user.id)
    response.delete_cookie(key="refresh_token", path="/api/v1/auth")
    return {"message": "Successfully logged out of all devices."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.get("/context", response_model=CurrentIdentityResponse)
async def get_current_identity_context(
    identity: CurrentIdentity = Depends(get_current_identity),
):
    user_res = UserResponse.model_validate(identity.user) if identity.user else None
    sa_res = None
    if identity.service_account:
        from app.domain.identity.schemas import ServiceAccountResponse
        sa_res = ServiceAccountResponse.model_validate(identity.service_account)

    return CurrentIdentityResponse(
        auth_type=identity.auth_type,
        request_id=identity.request_id,
        correlation_id=identity.correlation_id,
        user=user_res,
        service_account=sa_res,
        permissions=list(identity.permissions),
    )
