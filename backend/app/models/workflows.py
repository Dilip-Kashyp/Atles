import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base


class ToolInvocation(Base):
    __tablename__ = "tool_invocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    tool_name = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # 'github', 'jira', 'notion'
    request_payload = Column(JSONB, nullable=False, default=dict)
    response_payload = Column(JSONB, nullable=True)
    status = Column(String, nullable=False, default="PENDING")  # 'PENDING', 'SUCCESS', 'FAILED'
    error = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation")
