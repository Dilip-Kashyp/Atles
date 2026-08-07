"""
Identity Domain: SQLAlchemy models.

Tables in this module:
    users              — Atlas internal identity (NOT a Google/GitHub user)
    oauth_accounts     — Links external OAuth login providers to Atlas users
    sessions           — Server-side session records (enables revocation & device tracking)
    refresh_tokens     — Rotating opaque tokens (SHA-256 hashed, never raw)
    service_accounts   — Non-human bot/automation identities scoped to a workspace
    api_keys           — Workspace-scoped API keys (belonging to EITHER a user OR a service account)
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.infrastructure.database.base import Base, SoftDeleteMixin, TimestampMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    """
    Atlas canonical user identity.
    A User represents a person using Atlas. Soft-deleted users retain data for audit.
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(320), nullable=False)
    email_verified = Column(Boolean, nullable=False, default=False)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    locale = Column(String(10), nullable=False, default="en")
    timezone = Column(String(64), nullable=False, default="UTC")
    status = Column(String(20), nullable=False, default="active")  
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)

    
    oauth_accounts = relationship(
        "OAuthAccount", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "Session", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    credentials = relationship(
        "Credential", back_populates="owner", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_users_email_active",
            "email",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
        Index("ix_users_status", "status"),
        Index("ix_users_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} status={self.status!r}>"


class OAuthAccount(Base, TimestampMixin):
    """
    Links an external OAuth provider identity to an Atlas User.
    CRITICAL: Access/refresh tokens stored here are ONLY for identity login assertions.
    """

    __tablename__ = "oauth_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider = Column(String(50), nullable=False)  
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(320), nullable=True)
    provider_username = Column(String(255), nullable=True)
    provider_avatar = Column(Text, nullable=True)
    scopes = Column(ARRAY(Text), nullable=False, default=list)
    encrypted_access_token = Column("encrypted_access_token", Text, nullable=True)
    encrypted_refresh_token = Column("encrypted_refresh_token", Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    raw_profile = Column(JSONB, nullable=False, default=dict)

    
    user = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_user_id", name="uq_oauth_accounts_provider_user"
        ),
        Index("ix_oauth_accounts_user_id", "user_id"),
        Index("ix_oauth_accounts_provider_email", "provider_email"),
    )

    def __repr__(self) -> str:
        return f"<OAuthAccount provider={self.provider!r} provider_user_id={self.provider_user_id!r}>"


class Session(Base):
    """
    Server-side session record for device tracking, active session view, and revocation.
    """

    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_family = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_active_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    is_active = Column(Boolean, nullable=False, default=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(String(50), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    
    user = relationship("User", back_populates="sessions")
    refresh_tokens = relationship(
        "RefreshToken", back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_token_family", "token_family"),
        Index(
            "ix_sessions_active_user",
            "user_id",
            "is_active",
            postgresql_where="is_active = TRUE",
        ),
    )

    def __repr__(self) -> str:
        return f"<Session id={self.id} user_id={self.user_id} is_active={self.is_active}>"


class RefreshToken(Base):
    """
    Rotating refresh token record (SHA-256 hashed).
    """

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    replaced_by_id = Column(
        UUID(as_uuid=True),
        ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    
    session = relationship("Session", back_populates="refresh_tokens")
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} used={self.used_at is not None}>"


class ServiceAccount(Base, TimestampMixin):
    """
    Service Account representing non-human automation/bot identities in a workspace.
    """

    __tablename__ = "service_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status = Column(String(20), nullable=False, default="active")  
    created_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    
    role = relationship("Role")
    workspace = relationship("Workspace", back_populates="service_accounts")
    api_keys = relationship(
        "ApiKey", back_populates="service_account", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_service_accounts_workspace_id", "workspace_id"),
        Index("ix_service_accounts_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ServiceAccount id={self.id} name={self.name!r} workspace_id={self.workspace_id}>"


class ApiKey(Base, TimestampMixin):
    """
    Workspace API key for machine-to-machine authentication.
    Can belong to EITHER a User OR a ServiceAccount. Never forces automation onto human user credentials.
    """

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    service_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("service_accounts.id", ondelete="CASCADE"),
        nullable=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    key_prefix = Column(String(20), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True)
    scopes = Column(ARRAY(Text), nullable=False, default=list)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    
    user = relationship("User", foreign_keys=[user_id])
    service_account = relationship("ServiceAccount", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_workspace_id", "workspace_id"),
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_service_account_id", "service_account_id"),
        Index("ix_api_keys_key_hash", "key_hash"),
    )

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} name={self.name!r} prefix={self.key_prefix!r}>"
