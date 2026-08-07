"""
Identity Domain Pydantic Schemas.
"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    display_name: str | None = None
    avatar_url: str | None = None
    locale: str = "en"
    timezone: str = "UTC"


class UserCreate(UserBase):
    email_verified: bool = False
    status: str = "active"


class UserUpdate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    locale: str | None = None
    timezone: str | None = None


class UserResponse(UserBase):
    id: UUID
    email_verified: bool
    status: str
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class OAuthAccountResponse(BaseModel):
    id: UUID
    provider: str
    provider_user_id: str
    provider_email: str | None = None
    provider_username: str | None = None
    provider_avatar: str | None = None
    scopes: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    token_family: UUID
    ip_address: str | None = None
    user_agent: str | None = None
    last_active_at: datetime
    expires_at: datetime
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class ServiceAccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    role_name: str = "Developer"


class ServiceAccountResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: str | None = None
    role_id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    service_account_id: UUID | None = None
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class ApiKeyResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: UUID | None = None
    service_account_id: UUID | None = None
    name: str
    description: str | None = None
    key_prefix: str
    scopes: list[str]
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResponse(ApiKeyResponse):
    raw_key: str  


class AccountMergeRequest(BaseModel):
    secondary_user_id: UUID


class CurrentIdentityResponse(BaseModel):
    auth_type: str
    request_id: str
    correlation_id: str
    user: UserResponse | None = None
    service_account: ServiceAccountResponse | None = None
    permissions: list[str] = Field(default_factory=list)
