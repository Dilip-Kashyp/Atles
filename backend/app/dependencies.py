"""
FastAPI Dependencies for Enterprise Identity & Tenancy.

Provides:
- get_current_identity: Resolves complete CurrentIdentity (User or ServiceAccount + Permissions)
- get_current_workspace_context: Resolves CurrentWorkspaceContext (Workspace + Config + Policy)
- get_current_user: Convenience helper returning User
- get_current_workspace: Convenience helper returning Workspace
- require_permission: Dependency factory for RBAC permission checks
- require_role: Dependency factory for RBAC role checks
"""
from typing import Callable, Optional
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.context import CurrentIdentity, CurrentWorkspaceContext
from app.database.session import get_db
from app.domain.identity.models import User
from app.domain.identity.repository import ApiKeyRepository, ServiceAccountRepository, UserRepository
from app.domain.shared.exceptions import InsufficientPermissionsError, WorkspaceMembershipRequiredError
from app.domain.workspace.models import Workspace
from app.domain.workspace.services import PolicyService, RBACService, WorkspaceService
from app.infrastructure.security import hashing, tokens

security = HTTPBearer(auto_error=False)


async def get_current_identity(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_workspace_id: Optional[str] = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
) -> CurrentIdentity:
    """
    Resolve WHO or WHAT is executing this request once per request.
    Handles Bearer JWT, User API Keys, and Service Account API Keys.
    """
    request_id = request.headers.get("X-Request-ID") or tokens.generate_secure_token(16)
    correlation_id = request.headers.get("X-Correlation-ID") or request_id

    identity = CurrentIdentity(
        request_id=request_id,
        correlation_id=correlation_id,
    )

    # 1. Bearer JWT Access Token (Human User) or Query Parameter (for redirects)
    token_str = None
    if credentials and credentials.credentials:
        token_str = credentials.credentials
    elif request.query_params.get("token"):
        token_str = request.query_params.get("token")

    if token_str:
        payload = tokens.verify_access_token(token_str)
        if not payload or not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(UUID(payload["sub"]))
        if not user or user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is inactive or disabled.",
            )

        identity.user = user
        identity.auth_type = "jwt"

    # 2. X-API-Key Header (User or Service Account)
    elif x_api_key:
        api_key_repo = ApiKeyRepository(db)
        key_hash = hashing.hash_token(x_api_key)
        api_key_record = await api_key_repo.get_by_hash(key_hash)

        if not api_key_record or not api_key_record.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or inactive API key.",
            )

        identity.api_key = api_key_record

        if api_key_record.service_account_id:
            sa_repo = ServiceAccountRepository(db)
            sa = await sa_repo.get_by_id(api_key_record.service_account_id)
            if not sa or sa.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Associated service account is disabled.",
                )
            identity.service_account = sa
            identity.auth_type = "api_key_service_account"
        elif api_key_record.user_id:
            user_repo = UserRepository(db)
            user = await user_repo.get_by_id(api_key_record.user_id)
            if not user or user.status != "active":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Associated API key owner account is inactive.",
                )
            identity.user = user
            identity.auth_type = "api_key_user"

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Resolve Workspace & Permissions if X-Workspace-ID or path parameter supplied
    workspace_id_str = x_workspace_id or request.path_params.get("workspace_id")
    if workspace_id_str:
        try:
            ws_id = UUID(workspace_id_str)
            ws_service = WorkspaceService(db)
            rbac_service = RBACService(db)
            workspace = await ws_service.get_workspace_by_id(ws_id)
            identity.workspace = workspace
            identity.organization = workspace.organization

            if identity.user:
                identity.membership = await rbac_service.member_repo.get_membership(
                    ws_id, identity.user.id
                )
                identity.permissions = await rbac_service.get_user_permissions(
                    ws_id, identity.user.id
                )
            elif identity.service_account and identity.service_account.role:
                perms = set()
                for rp in identity.service_account.role.role_permissions:
                    if rp.permission:
                        perms.add(rp.permission.name)
                identity.permissions = perms
        except (ValueError, Exception):
            pass

    return identity


async def get_current_workspace_context(
    request: Request,
    identity: CurrentIdentity = Depends(get_current_identity),
    db: AsyncSession = Depends(get_db),
) -> CurrentWorkspaceContext:
    """
    Resolve workspace context for tenant-scoped operations.
    Requires X-Workspace-ID header or workspace_id path param.
    """
    ws_id_str = request.headers.get("X-Workspace-ID") or request.path_params.get("workspace_id")
    ws_service = WorkspaceService(db)
    policy_service = PolicyService(db)
    rbac_service = RBACService(db)

    if ws_id_str:
        try:
            ws_id = UUID(ws_id_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid workspace ID format.")
        workspace = await ws_service.get_workspace_by_id(ws_id)
    elif identity.user:
        workspaces = await ws_service.list_user_workspaces(identity.user.id)
        if not workspaces:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to any active workspace.",
            )
        workspace = workspaces[0]
    elif identity.service_account:
        workspace = await ws_service.get_workspace_by_id(identity.service_account.workspace_id)
    else:
        raise HTTPException(status_code=400, detail="Workspace context missing.")

    policy = await policy_service.get_policy(workspace.id)
    config = workspace.configuration

    permissions = identity.permissions
    if not permissions and identity.user:
        permissions = await rbac_service.get_user_permissions(workspace.id, identity.user.id)

    return CurrentWorkspaceContext(
        workspace=workspace,
        configuration=config,
        policy=policy,
        permissions=permissions,
    )


async def get_current_user(
    identity: CurrentIdentity = Depends(get_current_identity),
) -> User:
    if not identity.user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Human user identity required for this endpoint.",
        )
    return identity.user


async def get_current_workspace(
    context: CurrentWorkspaceContext = Depends(get_current_workspace_context),
) -> Workspace:
    return context.workspace


def require_permission(permission_name: str) -> Callable:
    async def dependency(
        identity: CurrentIdentity = Depends(get_current_identity),
        context: CurrentWorkspaceContext = Depends(get_current_workspace_context),
    ) -> None:
        if permission_name not in context.permissions and permission_name not in identity.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: '{permission_name}'",
            )
    return dependency


def require_role(role_name: str) -> Callable:
    async def dependency(
        identity: CurrentIdentity = Depends(get_current_identity),
        context: CurrentWorkspaceContext = Depends(get_current_workspace_context),
    ) -> None:
        role_match = False
        if identity.membership and identity.membership.role and identity.membership.role.name == role_name:
            role_match = True
        if not role_match:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role '{role_name}' is missing.",
            )
    return dependency


def get_workspace_membership(
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Legacy helper for backward compatibility with legacy endpoints."""
    return get_current_workspace(
        request=Request({"type": "http", "path": "/", "headers": []}),
        x_workspace_id=workspace_id,
        current_user=user,
        db=db,
    )


def get_orchestrator(request: Request):
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        raise HTTPException(status_code=500, detail="Orchestrator is not configured")
    return orchestrator


def get_slack_webhook_handler(request: Request):
    handler = getattr(request.app.state, "slack_webhook_handler", None)
    if handler is None:
        raise HTTPException(status_code=500, detail="Slack webhook handler is not configured")
    return handler


