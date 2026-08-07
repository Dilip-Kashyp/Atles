"""
API v1 Service Accounts Endpoints.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.domain.identity.repository import ServiceAccountRepository
from app.domain.identity.schemas import ServiceAccountCreate, ServiceAccountResponse
from app.domain.shared.exceptions import AtlasError
from app.domain.workspace.services import RBACService, ServiceAccountService

router = APIRouter(prefix="/workspaces/{workspace_id}/service-accounts", tags=["service-accounts"])


@router.get("", response_model=List[ServiceAccountResponse])
async def list_service_accounts(
    workspace_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "service_account:manage")

    sa_repo = ServiceAccountRepository(db)
    service_accounts = await sa_repo.list_by_workspace(workspace_id)
    return [ServiceAccountResponse.model_validate(sa) for sa in service_accounts]


@router.post("", response_model=ServiceAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_service_account(
    workspace_id: UUID,
    payload: ServiceAccountCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "service_account:manage")

    sa_service = ServiceAccountService(db)
    try:
        sa = await sa_service.create_service_account(
            workspace_id=workspace_id,
            name=payload.name,
            role_name=payload.role_name,
            description=payload.description,
            created_by_user_id=current_user.id,
        )
    except AtlasError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)

    return ServiceAccountResponse.model_validate(sa)


@router.delete("/{service_account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_account(
    workspace_id: UUID,
    service_account_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "service_account:manage")

    sa_repo = ServiceAccountRepository(db)
    success = await sa_repo.delete(service_account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Service account not found.")
