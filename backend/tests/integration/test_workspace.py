"""Integration tests for workspaces, memberships, and invitation flows."""
import pytest
from app.domain.identity.repository import UserRepository
from app.domain.workspace.repository import RoleRepository
from app.domain.workspace.services import InviteService, WorkspaceService


@pytest.mark.asyncio
async def test_workspace_creation_and_invitation_flow(db_session):
    import uuid
    user_repo = UserRepository(db_session)
    ws_service = WorkspaceService(db_session)
    invite_service = InviteService(db_session)
    role_repo = RoleRepository(db_session)

    await role_repo.seed_system_roles_and_permissions()

    owner_email = f"owner-{uuid.uuid4().hex[:8]}@acme.com"
    invitee_email = f"invitee-{uuid.uuid4().hex[:8]}@acme.com"
    owner = await user_repo.create(email=owner_email, display_name="Owner")
    invitee = await user_repo.create(email=invitee_email, display_name="Invitee")

    workspace, member = await ws_service.create_workspace(
        creator_user_id=owner.id, name="Acme Workspace"
    )

    assert workspace.name == "Acme Workspace"
    assert member.user_id == owner.id

    # Create invitation for invitee
    invite, raw_token = await invite_service.create_invitation(
        workspace_id=workspace.id,
        invited_by_user_id=owner.id,
        email=invitee_email,
        role_name="Developer",
    )

    assert invite.status == "pending"

    # Invitee accepts invitation
    new_member = await invite_service.accept_invitation(raw_token, invitee)
    assert new_member.workspace_id == workspace.id
    assert new_member.user_id == invitee.id
    assert new_member.role.name == "Developer"
