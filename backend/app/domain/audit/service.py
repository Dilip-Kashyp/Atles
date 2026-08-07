"""
Audit Domain Service & Event Subscriber.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.repository import AuditEventRepository
from app.domain.shared.events import AuditEvent as DomainAuditEvent, event_bus


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuditEventRepository(db)

    async def record_event(
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
        payload: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> None:
        await self.repo.log_event(
            event_type=event_type,
            resource_type=resource_type,
            actor_type=actor_type,
            actor_id=actor_id,
            workspace_id=workspace_id,
            organization_id=organization_id,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            payload=payload,
            correlation_id=correlation_id,
        )


async def handle_domain_audit_event(db: AsyncSession, event: DomainAuditEvent) -> None:
    service = AuditService(db)
    await service.record_event(
        event_type=event.event_type,
        resource_type=event.resource_type,
        actor_type=event.actor_type,
        actor_id=event.actor_id,
        workspace_id=event.workspace_id,
        organization_id=event.organization_id,
        resource_id=event.resource_id,
        ip_address=event.ip_address,
        user_agent=event.user_agent,
        payload=event.payload,
        correlation_id=event.correlation_id,
    )
