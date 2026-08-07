"""
Audit Domain Repository.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.models import AuditEvent


class AuditEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_event(
        self,
        event_type: str,
        resource_type: str,
        actor_type: str = "user",
        actor_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        resource_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        payload: Optional[dict] = None,
        correlation_id: Optional[str] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=event_type,
            resource_type=resource_type,
            actor_type=actor_type,
            actor_id=actor_id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            payload=payload or {},
            correlation_id=correlation_id,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def list_by_workspace(
        self, workspace_id: UUID, limit: int = 50
    ) -> List[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .filter(AuditEvent.workspace_id == workspace_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
