"""
API v1 API Keys Endpoints.

Handles creating and revoking API keys for human Users OR Service Accounts.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.domain.identity.repository import ApiKeyRepository
from app.domain.identity.schemas import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyResponse
from app.domain.workspace.services import RBACService
from app.infrastructure.security import hashing

router = APIRouter(prefix="/workspaces/{workspace_id}/api-keys", tags=["api-keys"])


@router.get("", response_model=List[ApiKeyResponse])
async def list_api_keys(
    workspace_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "api_key:manage")

    api_key_repo = ApiKeyRepository(db)
    keys = await api_key_repo.list_by_workspace(workspace_id)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    workspace_id: UUID,
    payload: ApiKeyCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "api_key:manage")

    # Generate raw key: atls_{prefix}_{32_chars}
    prefix_rand = hashing.generate_secure_token(4).lower()
    secret_rand = hashing.generate_secure_token(32)
    key_prefix = f"atls_{prefix_rand}"
    raw_key = f"{key_prefix}_{secret_rand}"
    key_hash = hashing.hash_token(raw_key)

    api_key_repo = ApiKeyRepository(db)

    user_id = current_user.id if not payload.service_account_id else None
    sa_id = payload.service_account_id if payload.service_account_id else None

    key_record = await api_key_repo.create(
        workspace_id=workspace_id,
        user_id=user_id,
        service_account_id=sa_id,
        name=payload.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        description=payload.description,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
    )

    res_dict = ApiKeyResponse.model_validate(key_record).model_dump()
    res_dict["raw_key"] = raw_key
    return ApiKeyCreateResponse(**res_dict)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    workspace_id: UUID,
    key_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "api_key:manage")

    api_key_repo = ApiKeyRepository(db)
    await api_key_repo.revoke(key_id, revoked_by_user_id=current_user.id)
