"""Tenancy models shim for backward compatibility."""
from app.domain.identity.models import User
from app.domain.workspace.models import Organization, Workspace, WorkspaceMember as Membership

__all__ = ["User", "Organization", "Workspace", "Membership"]
