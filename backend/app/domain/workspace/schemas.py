"""
Workspace Domain Pydantic Schemas.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.identity.schemas import UserResponse


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=100)
    logo_url: Optional[str] = None
    billing_email: Optional[EmailStr] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=100)
    logo_url: Optional[str] = None
    billing_email: Optional[EmailStr] = None


class OrganizationMemberResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    user: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    billing_email: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceConfigurationUpdate(BaseModel):
    timezone: Optional[str] = None
    branding: Optional[Dict[str, Any]] = None
    default_provider: Optional[str] = None
    ai_preferences: Optional[Dict[str, Any]] = None
    notification_preferences: Optional[Dict[str, Any]] = None


class WorkspaceConfigurationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    timezone: str
    branding: Dict[str, Any]
    default_provider: Optional[str] = None
    ai_preferences: Dict[str, Any]
    notification_preferences: Dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class WorkspacePolicyUpdate(BaseModel):
    require_mfa: Optional[bool] = None
    allow_guests: Optional[bool] = None
    allowed_integrations: Optional[List[str]] = None
    retention_days: Optional[int] = None
    default_ai_provider: Optional[str] = None
    api_restrictions: Optional[Dict[str, Any]] = None


class WorkspacePolicyResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    require_mfa: bool
    allow_guests: bool
    allowed_integrations: List[str]
    retention_days: int
    default_ai_provider: str
    api_restrictions: Dict[str, Any]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=100)
    org_id: Optional[UUID] = None
    icon_url: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, max_length=100)
    icon_url: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    slug: str
    icon_url: Optional[str] = None
    is_default: bool
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionResponse(BaseModel):
    id: UUID
    name: str
    domain: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    id: UUID
    workspace_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    is_system: bool
    permissions: List[PermissionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class WorkspaceMemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role_id: UUID
    status: str
    joined_at: datetime
    last_active_at: datetime
    user: Optional[UserResponse] = None
    role: Optional[RoleResponse] = None

    model_config = ConfigDict(from_attributes=True)


class InviteRequest(BaseModel):
    email: EmailStr
    role_id: Optional[UUID] = None
    role_name: Optional[str] = "Developer"


class InviteAcceptRequest(BaseModel):
    token: str


class InvitationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    invited_by_user_id: UUID
    email: str
    role_id: UUID
    status: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SwitchWorkspaceRequest(BaseModel):
    workspace_id: UUID
