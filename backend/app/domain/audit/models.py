"""
Audit Domain SQLAlchemy Model.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.infrastructure.database.base import Base


class AuditEvent(Base):
    """
    Immutable audit event log in PostgreSQL.
    """
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    actor_type = Column(String(30), nullable=False, default="user")  # 'user' | 'service_account' | 'system' | 'api_key'
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    workspace_id = Column(UUID(as_uuid=True), nullable=True)
    organization_id = Column(UUID(as_uuid=True), nullable=True)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=False, default=dict)
    correlation_id = Column(String(64), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_audit_events_event_type", "event_type"),
        Index("ix_audit_events_actor_id", "actor_id"),
        Index("ix_audit_events_workspace_id", "workspace_id"),
        Index("ix_audit_events_organization_id", "organization_id"),
        Index("ix_audit_events_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditEvent id={self.id} type={self.event_type!r} actor={self.actor_id}>"
