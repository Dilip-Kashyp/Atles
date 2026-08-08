import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.constants import INTEGRATION_V1_CALLBACK_URL
from app.context import CurrentIdentity
from app.database.session import get_db
from app.dependencies import get_current_identity
from app.domain.identity.providers import login_provider_registry
from app.domain.integrations.schemas import IntegrationResponse
from app.domain.integrations.service import IntegrationService
from app.domain.workspace.repository import WorkspaceRepository
from app.infrastructure.cache.redis import redis_client

router = APIRouter(prefix="/integrations", tags=["user_integrations"])
settings = get_settings()

def _resolve_redirect_uri(provider: str) -> str:
    return INTEGRATION_V1_CALLBACK_URL.format(provider=provider)

async def _get_personal_workspace_id(user_id: UUID, db: AsyncSession) -> UUID:
    ws_repo = WorkspaceRepository(db)
    workspaces = await ws_repo.list_by_user_id(user_id)
    if not workspaces:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User has no personal workspace."
        )
    return workspaces[0].id

@router.get("/available")
async def list_available_integrations():
    """Return the available tools that can be connected."""
    providers = []
    # Currently login_provider_registry contains the active providers
    # For a real system you'd filter out identity-only providers vs tools
    if login_provider_registry.is_supported("github"):
        providers.append({"id": "github", "name": "GitHub", "icon": "github"})
    if login_provider_registry.is_supported("slack"):
        providers.append({"id": "slack", "name": "Slack", "icon": "slack"})
    return providers

@router.get("/me", response_model=list[IntegrationResponse])
async def list_my_integrations(
    identity: CurrentIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db)
):
    """Return the integrations connected by the current user."""
    workspace_id = await _get_personal_workspace_id(identity.actor_id, db)
    service = IntegrationService(db)
    integrations = await service.get_integrations(workspace_id)
    return [IntegrationResponse.model_validate(i) for i in integrations]

@router.get("/me/{provider}/connect")
async def connect_my_integration(
    provider: str,
    request: Request,
    identity: CurrentIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db)
):
    """Initiates OAuth flow to connect an integration for the user."""
    if not login_provider_registry.is_supported(provider):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported integration provider: '{provider}'",
        )

    workspace_id = await _get_personal_workspace_id(identity.actor_id, db)

    provider_impl = login_provider_registry.get(provider)
    state = secrets.token_urlsafe(32)

    # Store state just like original integration flow
    state_val = f"{workspace_id}:{identity.actor_id}"
    await redis_client.setex(f"integration_state:{state}", 600, state_val)

    redirect_uri = _resolve_redirect_uri(provider)
    auth_url = provider_impl.get_authorization_url(state, redirect_uri)
    return RedirectResponse(auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

@router.delete("/me/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_my_integration(
    integration_id: UUID,
    identity: CurrentIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db)
):
    """Disconnects an integration connected to the user."""
    workspace_id = await _get_personal_workspace_id(identity.actor_id, db)
    service = IntegrationService(db)
    await service.disconnect_integration(integration_id, workspace_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

import httpx
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.models.integrations import Integration, IntegrationUser
from app.credentials.manager import CredentialManager
from app.domain.integrations.schemas import IntegrationUserResponse

@router.post("/me/{integration_id}/sync-users")
async def sync_integration_users(
    integration_id: UUID,
    identity: CurrentIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db)
):
    """Sync users from Slack channels into the database."""
    workspace_id = await _get_personal_workspace_id(identity.actor_id, db)
    
    result = await db.execute(
        select(Integration)
        .where(Integration.id == integration_id, Integration.workspace_id == workspace_id)
        .options(selectinload(Integration.credentials))
    )
    integration = result.scalars().first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
        
    if integration.provider_type != "slack":
        raise HTTPException(status_code=400, detail="Only Slack is supported for user sync")
        
    if not integration.credentials:
        raise HTTPException(status_code=400, detail="No credentials found")
        
    cred = integration.credentials[0]
    manager = CredentialManager()
    access_token = manager.decrypt(cred.encrypted_token)
    
    async with httpx.AsyncClient() as client:
        # 1. Fetch channels
        resp = await client.get(
            "https://slack.com/api/conversations.list",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"types": "public_channel", "exclude_archived": "true"}
        )
        data = resp.json()
        if not data.get("ok"):
            raise HTTPException(status_code=400, detail=f"Slack API error (conversations.list): {data.get('error')}")
            
        channels = data.get("channels", [])
        
        # 2. Fetch members for each channel
        unique_user_ids = set()
        for channel in channels:
            channel_id = channel.get("id")
            mem_resp = await client.get(
                "https://slack.com/api/conversations.members",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"channel": channel_id}
            )
            mem_data = mem_resp.json()
            if mem_data.get("ok"):
                for uid in mem_data.get("members", []):
                    unique_user_ids.add(uid)
                    
        # 3. Fetch all users to get profiles
        users_resp = await client.get(
            "https://slack.com/api/users.list",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        users_data = users_resp.json()
        if not users_data.get("ok"):
            raise HTTPException(status_code=400, detail=f"Slack API error (users.list): {users_data.get('error')}")
            
        all_users = users_data.get("members", [])
        
        # 4. Save mapped users to db
        await db.execute(delete(IntegrationUser).where(IntegrationUser.integration_id == integration_id))
        
        synced = 0
        for m in all_users:
            uid = m.get("id")
            if uid in unique_user_ids:
                user = IntegrationUser(
                    integration_id=integration_id,
                    provider_user_id=uid,
                    username=m.get("name"),
                    name=m.get("real_name") or m.get("profile", {}).get("real_name"),
                    email=m.get("profile", {}).get("email"),
                    avatar_url=m.get("profile", {}).get("image_192"),
                    is_bot=str(m.get("is_bot", False)),
                    raw_profile=m
                )
                db.add(user)
                synced += 1
                
        await db.commit()
        return {"status": "success", "synced_users": synced}

@router.get("/me/{integration_id}/users", response_model=list[IntegrationUserResponse])
async def list_integration_users(
    integration_id: UUID,
    identity: CurrentIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db)
):
    """List synced users for an integration."""
    workspace_id = await _get_personal_workspace_id(identity.actor_id, db)
    
    result = await db.execute(
        select(Integration).where(Integration.id == integration_id, Integration.workspace_id == workspace_id)
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Integration not found")
        
    users_result = await db.execute(
        select(IntegrationUser).where(IntegrationUser.integration_id == integration_id)
    )
    return [IntegrationUserResponse.model_validate(u) for u in users_result.scalars().all()]


@router.get("/me/all-users", response_model=list[IntegrationUserResponse])
async def list_all_integration_users(
    identity: CurrentIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db)
):
    """List all synced users across all integrations for the workspace."""
    workspace_id = await _get_personal_workspace_id(identity.actor_id, db)
    
    users_result = await db.execute(
        select(IntegrationUser)
        .join(Integration)
        .where(Integration.workspace_id == workspace_id)
    )
    return [IntegrationUserResponse.model_validate(u) for u in users_result.scalars().all()]


from pydantic import BaseModel

class UpdatePermissionsRequest(BaseModel):
    is_active: bool | None = None
    can_read: bool | None = None
    can_write: bool | None = None
    can_delete: bool | None = None

@router.patch("/me/users/{user_id}/permissions", response_model=IntegrationUserResponse)
async def update_integration_user_permissions(
    user_id: UUID,
    payload: UpdatePermissionsRequest,
    identity: CurrentIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db)
):
    """Update permissions for a specific integration user."""
    workspace_id = await _get_personal_workspace_id(identity.actor_id, db)
    
    result = await db.execute(
        select(IntegrationUser)
        .join(Integration)
        .where(
            IntegrationUser.id == user_id,
            Integration.workspace_id == workspace_id
        )
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Integration user not found")
        
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.can_read is not None:
        user.can_read = payload.can_read
    if payload.can_write is not None:
        user.can_write = payload.can_write
    if payload.can_delete is not None:
        user.can_delete = payload.can_delete
        
    await db.commit()
    await db.refresh(user)
    return IntegrationUserResponse.model_validate(user)
