from datetime import datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, ConfigDict


class WorkspaceCapabilityResponse(BaseModel):
    id: UUID
    capability: str
    
    model_config = ConfigDict(from_attributes=True)


class IntegrationResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    provider_type: str
    provider_variant: str
    type: str
    status: str
    created_at: datetime
    capabilities: list[WorkspaceCapabilityResponse] = []

    model_config = ConfigDict(from_attributes=True)


class IntegrationUserResponse(BaseModel):
    id: UUID
    integration_id: UUID
    provider_user_id: str
    username: str | None = None
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    is_bot: str | None = None
    
    is_active: bool
    can_read: bool
    can_write: bool
    can_delete: bool
    raw_profile: dict[str, Any] | None = None
    
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
