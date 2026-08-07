"""
Workspace Domain: SQLAlchemy models.

Tables in this module:
    organizations            — Root company or enterprise entity
    organization_domains     — Domain verification for auto-join / SSO
    organization_members     — Company-level membership & governance
    workspaces               — Primary tenancy boundary for all Atlas operational entities
    workspace_configuration  — Workspace settings (timezone, branding, providers)
    workspace_policies       — Enterprise security policies (MFA, guests, retention, restrictions)
    roles                    — Workspace RBAC roles (System + Custom)
    permissions              — Fine-grained system permissions
    role_permissions         — Mapping of roles to permissions
    workspace_members        — User membership within a workspace
    workspace_invitations    — Workspace invitation flow
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.infrastructure.database.base import Base, SoftDeleteMixin, TimestampMixin


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    """
    Organization representing a company or root enterprise entity.
    """

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    logo_url = Column(Text, nullable=True)
    billing_email = Column(String(320), nullable=True)
    status = Column(String(20), nullable=False, default="active")  
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)

    
    workspaces = relationship(
        "Workspace", back_populates="organization", cascade="all, delete-orphan"
    )
    domains = relationship(
        "OrganizationDomain", back_populates="organization", cascade="all, delete-orphan"
    )
    org_members = relationship(
        "OrganizationMember", back_populates="organization", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_organizations_slug_active",
            "slug",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r}>"


class OrganizationDomain(Base):
    """
    Verified domains owned by an organization (e.g. acme.com).
    Used for domain matching, auto-join policies, and future SAML SSO.
    """

    __tablename__ = "organization_domains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    domain = Column(String(255), nullable=False)
    is_verified = Column(Boolean, nullable=False, default=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    organization = relationship("Organization", back_populates="domains")

    __table_args__ = (
        UniqueConstraint("domain", name="uq_organization_domains_domain"),
        Index("ix_organization_domains_org_id", "org_id"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationDomain domain={self.domain!r} verified={self.is_verified}>"


class OrganizationMember(Base, TimestampMixin):
    """
    Company-level membership separate from workspace operational access.
    Manages enterprise governance, SSO rules, and organization-wide admin access.
    """

    __tablename__ = "organization_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String(20), nullable=False, default="MEMBER")  
    joined_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    organization = relationship("Organization", back_populates="org_members")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_members_user"),
        Index("ix_org_members_org_id", "organization_id"),
        Index("ix_org_members_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<OrganizationMember org={self.organization_id} user={self.user_id} role={self.role}>"


class Workspace(Base, TimestampMixin, SoftDeleteMixin):
    """
    Primary tenancy boundary in Atlas. All operational features belong to a Workspace.
    """

    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    icon_url = Column(Text, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    status = Column(String(20), nullable=False, default="active")  
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)

    
    organization = relationship("Organization", back_populates="workspaces")
    configuration = relationship(
        "WorkspaceConfiguration",
        back_populates="workspace",
        uselist=False,
        cascade="all, delete-orphan",
    )
    policy = relationship(
        "WorkspacePolicy",
        back_populates="workspace",
        uselist=False,
        cascade="all, delete-orphan",
    )
    members = relationship(
        "WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan"
    )
    roles = relationship(
        "Role", back_populates="workspace", cascade="all, delete-orphan"
    )
    invitations = relationship(
        "WorkspaceInvitation", back_populates="workspace", cascade="all, delete-orphan"
    )
    service_accounts = relationship(
        "ServiceAccount", back_populates="workspace", cascade="all, delete-orphan"
    )
    integrations = relationship(
        "Integration", back_populates="workspace", cascade="all, delete-orphan"
    )
    capabilities = relationship(
        "WorkspaceCapability", back_populates="workspace", cascade="all, delete-orphan"
    )
    conversations = relationship(
        "Conversation", back_populates="workspace", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index(
            "ix_workspaces_org_slug_active",
            "org_id",
            "slug",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
        Index("ix_workspaces_org_id", "org_id"),
    )

    def __repr__(self) -> str:
        return f"<Workspace id={self.id} slug={self.slug!r}>"


class WorkspaceConfiguration(Base):
    """
    Structured workspace configuration options to avoid monolithic JSON blobs.
    """

    __tablename__ = "workspace_configuration"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    timezone = Column(String(64), nullable=False, default="UTC")
    branding = Column(JSONB, nullable=False, default=dict)
    default_provider = Column(String(50), nullable=True)
    ai_preferences = Column(JSONB, nullable=False, default=dict)
    notification_preferences = Column(JSONB, nullable=False, default=dict)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    workspace = relationship("Workspace", back_populates="configuration")

    def __repr__(self) -> str:
        return f"<WorkspaceConfiguration workspace_id={self.workspace_id}>"


class WorkspacePolicy(Base):
    """
    Enterprise security policies for a workspace.
    """

    __tablename__ = "workspace_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    require_mfa = Column(Boolean, nullable=False, default=False)
    allow_guests = Column(Boolean, nullable=False, default=True)
    allowed_integrations = Column(ARRAY(Text), nullable=False, default=list)
    retention_days = Column(Integer, nullable=False, default=365)
    default_ai_provider = Column(String(50), nullable=False, default="gemini")
    api_restrictions = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    workspace = relationship("Workspace", back_populates="policy")

    def __repr__(self) -> str:
        return f"<WorkspacePolicy workspace_id={self.workspace_id}>"


class Role(Base):
    """
    Role definitions for RBAC.
    workspace_id IS NULL implies System Roles (Owner, Admin, Manager, Developer, Viewer).
    """

    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=True,
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    workspace = relationship("Workspace", back_populates="roles")
    role_permissions = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_roles_workspace_name", "workspace_id", "name", unique=True),
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name!r} is_system={self.is_system}>"


class Permission(Base):
    """
    Granular permission definitions.
    """

    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    domain = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    role_permissions = relationship(
        "RolePermission", back_populates="permission", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Permission name={self.name!r} domain={self.domain!r}>"


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")

    def __repr__(self) -> str:
        return f"<RolePermission role_id={self.role_id} permission_id={self.permission_id}>"


class WorkspaceMember(Base, TimestampMixin):
    __tablename__ = "workspace_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    joined_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_active_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    status = Column(String(20), nullable=False, default="active")

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User")
    role = relationship("Role")

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_user"),
        Index("ix_workspace_members_workspace_id", "workspace_id"),
        Index("ix_workspace_members_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<WorkspaceMember workspace_id={self.workspace_id} user_id={self.user_id}>"


class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    invited_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    email = Column(String(320), nullable=False)
    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    token_hash = Column(String(64), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="pending")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    workspace = relationship("Workspace", back_populates="invitations")
    invited_by = relationship("User", foreign_keys=[invited_by_user_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id])
    role = relationship("Role")

    __table_args__ = (
        Index("ix_workspace_invitations_workspace_id", "workspace_id"),
        Index("ix_workspace_invitations_email", "email"),
        Index("ix_workspace_invitations_token_hash", "token_hash"),
    )

    def __repr__(self) -> str:
        return f"<WorkspaceInvitation email={self.email!r} status={self.status!r}>"
