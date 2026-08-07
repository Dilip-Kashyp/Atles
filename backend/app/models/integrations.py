import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    provider_type = Column(String, nullable=False)  
    provider_variant = Column(String, nullable=False)  
    provider_workspace_id = Column(String, nullable=True, index=True) 
    type = Column(String, nullable=False, default="WORKSPACE")  
    status = Column(String, nullable=False, default="CONNECTED")  
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace", back_populates="integrations")
    credentials = relationship("Credential", back_populates="integration", cascade="all, delete-orphan")
    capabilities = relationship("WorkspaceCapability", back_populates="integration", cascade="all, delete-orphan")


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    encrypted_token = Column(LargeBinary, nullable=False)
    encrypted_refresh = Column(LargeBinary, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    integration = relationship("Integration", back_populates="credentials")
    owner = relationship("User", back_populates="credentials")


class WorkspaceCapability(Base):
    __tablename__ = "workspace_capabilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    capability = Column(String, nullable=False)  
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    workspace = relationship("Workspace", back_populates="capabilities")
    integration = relationship("Integration", back_populates="capabilities")
