from datetime import datetime
from uuid import UUID

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
