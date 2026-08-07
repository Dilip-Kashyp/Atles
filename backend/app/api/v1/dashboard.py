
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.session import get_db
from app.dependencies import get_current_user, get_workspace_membership
from app.models.integrations import Integration, WorkspaceCapability
from app.models.tenancy import Membership, User, Workspace

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    role: str

    class Config:
        from_attributes = True


class IntegrationResponse(BaseModel):
    id: str
    provider_type: str
    provider_variant: str
    type: str
    status: str
    connected_by: str

    class Config:
        from_attributes = True


class CapabilityMappingRequest(BaseModel):
    capability: str
    integration_id: str


@router.get("/workspaces", response_model=list[WorkspaceResponse])
async def get_workspaces(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List workspaces the authenticated user belongs to."""
    result = await db.execute(
        select(Workspace.id, Workspace.name, Membership.role)
        .join(Membership, Workspace.id == Membership.workspace_id)
        .filter(Membership.user_id == user.id)
    )
    workspaces = result.all()
    return [
        WorkspaceResponse(id=str(w.id), name=w.name, role=w.role)
        for w in workspaces
    ]


@router.get("/workspaces/{workspace_id}/integrations", response_model=list[IntegrationResponse])
async def get_integrations(
    workspace_id: str,
    membership: Membership = Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    """Get active/disconnected integrations for a specific workspace."""
    result = await db.execute(
        select(
            Integration.id,
            Integration.provider_type,
            Integration.provider_variant,
            Integration.type,
            Integration.status,
            User.name.label("connected_by"),
        )
        .join(User, Integration.credentials.any(owner_user_id=User.id), isouter=True)
        .filter(Integration.workspace_id == workspace_id)
    )
    integrations = result.all()
    return [
        IntegrationResponse(
            id=str(i.id),
            provider_type=i.provider_type,
            provider_variant=i.provider_variant,
            type=i.type,
            status=i.status,
            connected_by=i.connected_by or "System",
        )
        for i in integrations
    ]


@router.delete("/workspaces/{workspace_id}/integrations/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_integration(
    workspace_id: str,
    integration_id: str,
    membership: Membership = Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect/Delete an integration in the workspace."""
    
    if membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Workspace admins/owners can disconnect integrations.",
        )

    result = await db.execute(
        select(Integration).filter(
            Integration.id == integration_id,
            Integration.workspace_id == workspace_id,
        )
    )
    integration = result.scalars().first()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    await db.delete(integration)
    await db.commit()


@router.get("/workspaces/{workspace_id}/capabilities")
async def get_capabilities(
    workspace_id: str,
    membership: Membership = Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    """Get all capability mappings for the workspace."""
    result = await db.execute(
        select(WorkspaceCapability).filter(WorkspaceCapability.workspace_id == workspace_id)
    )
    mappings = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "capability": m.capability,
            "integration_id": str(m.integration_id),
        }
        for m in mappings
    ]


@router.post("/workspaces/{workspace_id}/capabilities", status_code=status.HTTP_200_OK)
async def update_capability_mapping(
    workspace_id: str,
    payload: CapabilityMappingRequest,
    membership: Membership = Depends(get_workspace_membership),
    db: AsyncSession = Depends(get_db),
):
    """Upsert a capability routing rule to map a capability to an integration."""
    if membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Workspace admins/owners can update capability mappings.",
        )

    
    result = await db.execute(
        select(Integration).filter(
            Integration.id == payload.integration_id,
            Integration.workspace_id == workspace_id,
        )
    )
    integration = result.scalars().first()
    if not integration:
        raise HTTPException(
            status_code=400,
            detail="Target integration does not exist in this workspace",
        )

    
    cap_result = await db.execute(
        select(WorkspaceCapability).filter(
            WorkspaceCapability.workspace_id == workspace_id,
            WorkspaceCapability.capability == payload.capability,
        )
    )
    mapping = cap_result.scalars().first()

    if mapping:
        mapping.integration_id = payload.integration_id
    else:
        mapping = WorkspaceCapability(
            workspace_id=workspace_id,
            capability=payload.capability,
            integration_id=payload.integration_id,
        )
        db.add(mapping)

    await db.commit()
    return {
        "message": "Capability mapping updated successfully",
        "capability": payload.capability,
        "integration_id": payload.integration_id,
    }
