import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.context import CurrentIdentity, CurrentWorkspaceContext
from app.database.session import get_db
from app.dependencies import get_current_identity, get_current_workspace_context
from app.domain.identity.providers import login_provider_registry
from app.domain.integrations.schemas import IntegrationResponse
from app.domain.integrations.service import IntegrationService
from app.infrastructure.cache.redis import redis_client

router = APIRouter(prefix="/workspaces", tags=["integrations"])
settings = get_settings()


def _resolve_redirect_uri(provider: str) -> str:
    
    return f"http://localhost:8000/api/v1/workspaces/integrations/{provider}/callback"


@router.get("/{workspace_id}/integrations/{provider}/connect")
async def connect_integration(
    workspace_id: UUID,
    provider: str,
    request: Request,
    context: CurrentWorkspaceContext = Depends(get_current_workspace_context),
    identity: CurrentIdentity = Depends(get_current_identity)
):
    if not login_provider_registry.is_supported(provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported integration provider: '{provider}'",
        )

    provider_impl = login_provider_registry.get(provider)
    state = secrets.token_urlsafe(32)

    
    state_val = f"{workspace_id}:{identity.actor_id}"
    await redis_client.setex(f"integration_state:{state}", 600, state_val)

    redirect_uri = _resolve_redirect_uri(provider)
    auth_url = provider_impl.get_authorization_url(state, redirect_uri)
    return RedirectResponse(auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/integrations/{provider}/callback")
async def connect_integration_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    state_key = f"integration_state:{state}"
    saved_state = await redis_client.get(state_key)
    if not saved_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired integration state parameter.",
        )
    await redis_client.delete(state_key)

    state_parts = saved_state.split(":")
    saved_workspace_id = state_parts[0]
    actor_id = state_parts[1]
    
    workspace_id = UUID(saved_workspace_id)

    if not login_provider_registry.is_supported(provider):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    provider_impl = login_provider_registry.get(provider)
    redirect_uri = _resolve_redirect_uri(provider)
    
    try:
        token_payload = await provider_impl.exchange_code(code, redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Provider token exchange failed: {e!s}")

    service = IntegrationService(db)
    await service.connect_integration(
        workspace_id=workspace_id,
        user_id=UUID(actor_id),
        provider=provider,
        token_data=token_payload
    )

    frontend_origin = settings.frontend_origin.rstrip("/")
    frontend_redirect = f"{frontend_origin}/integrations"
    return RedirectResponse(frontend_redirect, status_code=status.HTTP_302_FOUND)


@router.get("/{workspace_id}/integrations", response_model=list[IntegrationResponse])
async def list_integrations(
    workspace_id: UUID,
    context: CurrentWorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    service = IntegrationService(db)
    integrations = await service.get_integrations(workspace_id)
    return [IntegrationResponse.model_validate(i) for i in integrations]


@router.delete("/{workspace_id}/integrations/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_integration(
    workspace_id: UUID,
    integration_id: UUID,
    context: CurrentWorkspaceContext = Depends(get_current_workspace_context),
    db: AsyncSession = Depends(get_db)
):
    service = IntegrationService(db)
    await service.disconnect_integration(integration_id, workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
