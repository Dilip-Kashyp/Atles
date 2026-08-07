"""Unit tests for RBAC permissions & role seeding."""
import pytest
from app.domain.workspace.repository import RoleRepository
from app.domain.workspace.services import RBACService, WorkspaceService
from app.domain.identity.repository import UserRepository


@pytest.mark.asyncio
async def test_role_seeding_and_rbac(db_session):
    role_repo = RoleRepository(db_session)
    await role_repo.seed_system_roles_and_permissions()

    owner_role = await role_repo.get_by_name("Owner")
    assert owner_role is not None
    assert owner_role.is_system is True

    perms = [rp.permission.name for rp in owner_role.role_permissions]
    assert "workspace:read" in perms
    assert "workspace:delete" in perms

    viewer_role = await role_repo.get_by_name("Viewer")
    assert viewer_role is not None
    viewer_perms = [rp.permission.name for rp in viewer_role.role_permissions]
    assert "workspace:read" in viewer_perms
    assert "workspace:delete" not in viewer_perms
