"""
API v1 Organizations Endpoints.

Handles organization management and organization-level members.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.dependencies import get_current_user
from app.domain.shared.exceptions import AtlasError
from app.domain.workspace.repository import OrgMemberRepository
from app.domain.workspace.schemas import (
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.domain.workspace.services import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_service = OrganizationService(db)
    try:
        org = await org_service.create_organization(
            name=payload.name,
            creator_user_id=current_user.id,
            slug=payload.slug,
            logo_url=payload.logo_url,
            billing_email=payload.billing_email,
        )
    except AtlasError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)

    return OrganizationResponse.model_validate(org)


@router.get("/{id}", response_model=OrganizationResponse)
async def get_organization(
    id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_service = OrganizationService(db)
    try:
        org = await org_service.get_by_id(id)
    except AtlasError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)

    return OrganizationResponse.model_validate(org)


@router.patch("/{id}", response_model=OrganizationResponse)
async def update_organization(
    id: UUID,
    payload: OrganizationUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_service = OrganizationService(db)
    try:
        org = await org_service.get_by_id(id)
        if payload.name:
            org.name = payload.name
        if payload.logo_url is not None:
            org.logo_url = payload.logo_url
        if payload.billing_email is not None:
            org.billing_email = payload.billing_email

        updated_org = await org_service.org_repo.update(org)
    except AtlasError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message)

    return OrganizationResponse.model_validate(updated_org)


@router.get("/{id}/members", response_model=List[OrganizationMemberResponse])
async def list_organization_members(
    id: UUID,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_mem_repo = OrgMemberRepository(db)
    members = await org_mem_repo.list_by_org(id)
    return [OrganizationMemberResponse.model_validate(m) for m in members]
