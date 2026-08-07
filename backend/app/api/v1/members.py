"""
API v1 Workspace Memberships & Invitations Endpoints.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.domain.shared.exceptions import AtlasError
from app.domain.workspace.repository import MemberRepository
from app.domain.workspace.schemas import (
    InviteAcceptRequest,
    InviteRequest,
    InvitationResponse,
    WorkspaceMemberResponse,
)
from app.domain.workspace.services import InviteService, RBACService

router = APIRouter(prefix="/workspaces", tags=["memberships"])


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def list_workspace_members(
    workspace_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "member:read")

    member_repo = MemberRepository(db)
    members = await member_repo.list_by_workspace_id(workspace_id)
    return [WorkspaceMemberResponse.model_validate(m) for m in members]


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "member:manage")

    member_repo = MemberRepository(db)
    success = await member_repo.remove(workspace_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Member not found in workspace.")


@router.post("/{workspace_id}/invite", response_model=InvitationResponse)
async def invite_member(
    workspace_id: UUID,
    payload: InviteRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rbac_service = RBACService(db)
    await rbac_service.require_permission(workspace_id, current_user.id, "member:invite")

    invite_service = InviteService(db)
    try:
        invite, raw_token = await invite_service.create_invitation(
            workspace_id=workspace_id,
            invited_by_user_id=current_user.id,
            email=payload.email,
            role_id=payload.role_id,
            role_name=payload.role_name,
        )
    except AtlasError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)

    return InvitationResponse.model_validate(invite)


@router.post("/invitations/{token}/accept", response_model=WorkspaceMemberResponse)
async def accept_invitation(
    token: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    invite_service = InviteService(db)
    try:
        member = await invite_service.accept_invitation(token, current_user)
    except AtlasError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)

    return WorkspaceMemberResponse.model_validate(member)
