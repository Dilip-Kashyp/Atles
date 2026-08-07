"""Tenancy models shim for backward compatibility."""
from app.domain.identity.models import User
from app.domain.workspace.models import Organization, Workspace
from app.domain.workspace.models import WorkspaceMember as Membership

__all__ = ["Membership", "Organization", "User", "Workspace"]
