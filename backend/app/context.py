"""
Request & Workspace Context Models.

Provides:
- CurrentIdentity: Unified context resolving identity, session, org, workspace, permissions, and request correlation.
- CurrentWorkspaceContext: Resolved workspace context for tenant-scoped operations.
"""
from dataclasses import dataclass, field
from typing import Optional, Set
from uuid import UUID, uuid4

from app.domain.identity.models import ApiKey, ServiceAccount, Session, User
from app.domain.workspace.models import (
    Organization,
    Workspace,
    WorkspaceConfiguration,
    WorkspaceMember,
    WorkspacePolicy,
)


@dataclass
class CurrentIdentity:
    """
    Resolved once per incoming request.
    Identifies WHO or WHAT is making the call (human User or automated ServiceAccount).
    """
    request_id: str = field(default_factory=lambda: str(uuid4()))
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    auth_type: str = "anonymous"  # 'jwt' | 'api_key_user' | 'api_key_service_account' | 'anonymous'

    user: Optional[User] = None
    service_account: Optional[ServiceAccount] = None
    session: Optional[Session] = None
    api_key: Optional[ApiKey] = None

    organization: Optional[Organization] = None
    workspace: Optional[Workspace] = None
    membership: Optional[WorkspaceMember] = None
    permissions: Set[str] = field(default_factory=set)

    @property
    def is_authenticated(self) -> bool:
        return self.user is not None or self.service_account is not None

    @property
    def is_service_account(self) -> bool:
        return self.service_account is not None

    @property
    def actor_id(self) -> Optional[UUID]:
        if self.user:
            return self.user.id
        if self.service_account:
            return self.service_account.id
        return None

    @property
    def actor_type(self) -> str:
        if self.user:
            return "user"
        if self.service_account:
            return "service_account"
        return "anonymous"


@dataclass
class CurrentWorkspaceContext:
    """
    Resolved per workspace-scoped request from X-Workspace-ID header or route param.
    """
    workspace: Workspace
    configuration: WorkspaceConfiguration
    policy: WorkspacePolicy
    permissions: Set[str] = field(default_factory=set)
