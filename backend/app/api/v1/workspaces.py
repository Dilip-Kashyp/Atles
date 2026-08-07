"""
API v1 Workspaces Endpoints.

Handles workspace creation, configuration, security policies, switching, and context.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.context import CurrentIdentity, CurrentWorkspaceContext
from app.database.session import get_db
from app.dependencies import (
    get_current_identity,
    get_current_user,
    get_current_workspace_context,
)
from app.domain.workspace.schemas import (
    SwitchWorkspaceRequest,
    WorkspaceConfigurationResponse,
    WorkspaceConfigurationUpdate,
    WorkspaceCreate,
    WorkspacePolicyResponse,
    WorkspacePolicyUpdate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.domain.workspace.services import PolicyService, RBACService, WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
async def list_user_workspaces(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_service = WorkspaceService(db)
    workspaces = await ws_service.list_user_workspaces(current_user.id)
    return [WorkspaceResponse.model_validate(w) for w in workspaces]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_service = WorkspaceService(db)
    workspace, member = await ws_service.create_workspace(
        creator_user_id=current_user.id,
        name=payload.name,
        org_id=payload.org_id,
        slug=payload.slug,
        icon_url=payload.icon_url,
    )
    return WorkspaceResponse.model_validate(workspace)


@router.get("/current", response_model=WorkspaceResponse)
async def get_current_active_workspace(
    context: CurrentWorkspaceContext = Depends(get_current_workspace_context),
):
    return WorkspaceResponse.model_validate(context.workspace)


@router.post("/switch", response_model=WorkspaceResponse)
async def switch_active_workspace(
    payload: SwitchWorkspaceRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws_service = WorkspaceService(db)
    rbac_service = RBACService(db)

    workspace = await ws_service.get_workspace_by_id(payload.workspace_id)
    perms = await rbac_service.get_user_permissions(workspace.id, current_user.id)

    if not perms:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an active member of this workspace.",
        )

    return WorkspaceResponse.model_validate(workspace)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    payload: WorkspaceUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "workspace:write")

    ws_service = WorkspaceService(db)
    workspace = await ws_service.get_workspace_by_id(workspace_id)

    if payload.name:
        workspace.name = payload.name
    if payload.icon_url is not None:
        workspace.icon_url = payload.icon_url

    updated_ws = await ws_service.ws_repo.update(workspace)
    return WorkspaceResponse.model_validate(updated_ws)


@router.get("/{workspace_id}/configuration", response_model=WorkspaceConfigurationResponse)
async def get_workspace_configuration(
    workspace_id: UUID,
    context: CurrentWorkspaceContext = Depends(get_current_workspace_context),
):
    return WorkspaceConfigurationResponse.model_validate(context.configuration)


@router.patch("/{workspace_id}/configuration", response_model=WorkspaceConfigurationResponse)
async def update_workspace_configuration(
    workspace_id: UUID,
    payload: WorkspaceConfigurationUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "workspace:write")

    ws_service = WorkspaceService(db)
    workspace = await ws_service.get_workspace_by_id(workspace_id)
    config = workspace.configuration

    if payload.timezone is not None:
        config.timezone = payload.timezone
    if payload.branding is not None:
        config.branding = payload.branding
    if payload.default_provider is not None:
        config.default_provider = payload.default_provider
    if payload.ai_preferences is not None:
        config.ai_preferences = payload.ai_preferences
    if payload.notification_preferences is not None:
        config.notification_preferences = payload.notification_preferences

    await db.flush()
    return WorkspaceConfigurationResponse.model_validate(config)


@router.get("/{workspace_id}/policies", response_model=WorkspacePolicyResponse)
async def get_workspace_policies(
    workspace_id: UUID,
    context: CurrentWorkspaceContext = Depends(get_current_workspace_context),
):
    return WorkspacePolicyResponse.model_validate(context.policy)


@router.patch("/{workspace_id}/policies", response_model=WorkspacePolicyResponse)
async def update_workspace_policies(
    workspace_id: UUID,
    payload: WorkspacePolicyUpdate,
    identity: CurrentIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, identity.actor_id, "policy:manage")

    policy_service = PolicyService(db)
    updated = await policy_service.update_policy(
        workspace_id=workspace_id,
        require_mfa=payload.require_mfa,
        allow_guests=payload.allow_guests,
        allowed_integrations=payload.allowed_integrations,
        retention_days=payload.retention_days,
        default_ai_provider=payload.default_ai_provider,
        api_restrictions=payload.api_restrictions,
        actor_id=identity.actor_id,
    )
    return WorkspacePolicyResponse.model_validate(updated)
