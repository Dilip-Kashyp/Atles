"""
Integration Service.
"""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.integrations import Integration, Credential, WorkspaceCapability
from app.credentials.manager import CredentialManager


class IntegrationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.cred_manager = CredentialManager()

    async def get_integrations(self, workspace_id: UUID) -> List[Integration]:
        result = await self.db.execute(
            select(Integration)
            .where(Integration.workspace_id == workspace_id)
            .options(selectinload(Integration.capabilities))
        )
        return list(result.scalars().all())

    async def connect_integration(
        self,
        workspace_id: UUID,
        user_id: UUID,
        provider: str,
        token_data: Dict[str, Any]
    ) -> Integration:
        """Create or update an integration based on OAuth token exchange."""
        
        # Check if already connected for this workspace
        result = await self.db.execute(
            select(Integration)
            .where(
                Integration.workspace_id == workspace_id,
                Integration.provider_type == provider
            )
            .options(selectinload(Integration.credentials), selectinload(Integration.capabilities))
        )
        integration = result.scalars().first()

        is_new = False
        if not integration:
            integration = Integration(
                workspace_id=workspace_id,
                provider_type=provider,
                provider_variant=f"{provider}_cloud", # Default variant
                type="WORKSPACE",
                status="CONNECTED"
            )
            self.db.add(integration)
            await self.db.flush()
            is_new = True
        else:
            integration.status = "CONNECTED"

        # Update or create credentials
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")
        
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        encrypted_access = self.cred_manager.encrypt(access_token) if access_token else b""
        encrypted_refresh = self.cred_manager.encrypt(refresh_token) if refresh_token else None

        if not is_new and integration.credentials:
            cred = integration.credentials[0]
            cred.encrypted_token = encrypted_access
            cred.encrypted_refresh = encrypted_refresh
            cred.expires_at = expires_at
            cred.owner_user_id = user_id
        else:
            cred = Credential(
                integration_id=integration.id,
                owner_user_id=user_id,
                encrypted_token=encrypted_access,
                encrypted_refresh=encrypted_refresh,
                expires_at=expires_at
            )
            self.db.add(cred)

        # Update capabilities (basic sync for now)
        # Delete existing ones and recreate
        if not is_new:
            for cap in integration.capabilities:
                await self.db.delete(cap)
        
        default_capabilities = []
        if provider == "slack":
            default_capabilities = ["chat:write", "channels:read"]
        elif provider == "github":
            default_capabilities = ["repo:read", "issue:write"]
            
        for cap_str in default_capabilities:
            cap = WorkspaceCapability(
                workspace_id=workspace_id,
                integration_id=integration.id,
                capability=cap_str
            )
            self.db.add(cap)

        await self.db.commit()
        await self.db.refresh(integration)
        return integration

    async def disconnect_integration(self, integration_id: UUID, workspace_id: UUID) -> None:
        result = await self.db.execute(
            select(Integration)
            .where(
                Integration.id == integration_id,
                Integration.workspace_id == workspace_id
            )
        )
        integration = result.scalars().first()
        if integration:
            await self.db.delete(integration)
            await self.db.commit()
