"""
Identity Domain Pydantic Schemas.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    locale: str = "en"
    timezone: str = "UTC"


class UserCreate(UserBase):
    email_verified: bool = False
    status: str = "active"


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    email_verified: bool
    status: str
    metadata_: Dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class OAuthAccountResponse(BaseModel):
    id: UUID
    provider: str
    provider_user_id: str
    provider_email: Optional[str] = None
    provider_username: Optional[str] = None
    provider_avatar: Optional[str] = None
    scopes: List[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    token_family: UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    last_active_at: datetime
    expires_at: datetime
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class ServiceAccountCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    role_name: str = "Developer"


class ServiceAccountResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str] = None
    role_id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    service_account_id: Optional[UUID] = None
    scopes: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    user_id: Optional[UUID] = None
    service_account_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    key_prefix: str
    scopes: List[str]
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyCreateResponse(ApiKeyResponse):
    raw_key: str  # Displayed ONCE at creation


class AccountMergeRequest(BaseModel):
    secondary_user_id: UUID


class CurrentIdentityResponse(BaseModel):
    auth_type: str
    request_id: str
    correlation_id: str
    user: Optional[UserResponse] = None
    service_account: Optional[ServiceAccountResponse] = None
    permissions: List[str] = Field(default_factory=list)
