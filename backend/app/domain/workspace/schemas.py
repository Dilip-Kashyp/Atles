"""
Workspace Domain Pydantic Schemas.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.identity.schemas import UserResponse


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=100)
    logo_url: str | None = None
    billing_email: EmailStr | None = None


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=100)
    logo_url: str | None = None
    billing_email: EmailStr | None = None


class OrganizationMemberResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    user: UserResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    logo_url: str | None = None
    billing_email: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceConfigurationUpdate(BaseModel):
    timezone: str | None = None
    branding: dict[str, Any] | None = None
    default_provider: str | None = None
    ai_preferences: dict[str, Any] | None = None
    notification_preferences: dict[str, Any] | None = None


class WorkspaceConfigurationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    timezone: str
    branding: dict[str, Any]
    default_provider: str | None = None
    ai_preferences: dict[str, Any]
    notification_preferences: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class WorkspacePolicyUpdate(BaseModel):
    require_mfa: bool | None = None
    allow_guests: bool | None = None
    allowed_integrations: list[str] | None = None
    retention_days: int | None = None
    default_ai_provider: str | None = None
    api_restrictions: dict[str, Any] | None = None


class WorkspacePolicyResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    require_mfa: bool
    allow_guests: bool
    allowed_integrations: list[str]
    retention_days: int
    default_ai_provider: str
    api_restrictions: dict[str, Any]
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=100)
    org_id: UUID | None = None
    icon_url: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(None, max_length=100)
    icon_url: str | None = None


class WorkspaceResponse(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    slug: str
    icon_url: str | None = None
    is_default: bool
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionResponse(BaseModel):
    id: UUID
    name: str
    domain: str
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(BaseModel):
    id: UUID
    workspace_id: UUID | None = None
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[PermissionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class WorkspaceMemberResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID
    role_id: UUID
    status: str
    joined_at: datetime
    last_active_at: datetime
    user: UserResponse | None = None
    role: RoleResponse | None = None

    model_config = ConfigDict(from_attributes=True)


class InviteRequest(BaseModel):
    email: EmailStr
    role_id: UUID | None = None
    role_name: str | None = "Developer"


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
    accepted_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SwitchWorkspaceRequest(BaseModel):
    workspace_id: UUID
