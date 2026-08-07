"""Integration tests for Workspace Security Policies and Configuration."""
import uuid
import pytest
from app.domain.identity.repository import UserRepository
from app.domain.workspace.services import PolicyService, WorkspaceService


@pytest.mark.asyncio
async def test_workspace_policies_and_config(db_session):
    user_repo = UserRepository(db_session)
    ws_service = WorkspaceService(db_session)
    policy_service = PolicyService(db_session)

    owner = await user_repo.create(email=f"owner-{uuid.uuid4().hex[:8]}@enterprise.com")
    workspace, _ = await ws_service.create_workspace(creator_user_id=owner.id, name="Secure Enterprise WS")

    # Get default policy
    policy = await policy_service.get_policy(workspace.id)
    assert policy.require_mfa is False
    assert policy.retention_days == 365

    # Update policy
    updated_policy = await policy_service.update_policy(
        workspace_id=workspace.id,
        require_mfa=True,
        allow_guests=False,
        allowed_integrations=["github", "slack"],
        retention_days=730,
        actor_id=owner.id,
    )

    assert updated_policy.require_mfa is True
    assert updated_policy.allow_guests is False
    assert "github" in updated_policy.allowed_integrations
    assert updated_policy.retention_days == 730
