"""Integration tests for identity provisioning and OAuth user flows."""
import pytest
from app.domain.identity.services import IdentityService
from app.domain.workspace.services import WorkspaceService


@pytest.mark.asyncio
async def test_find_or_create_user_oauth(db_session):
    import uuid
    identity_service = IdentityService(db_session)
    ws_service = WorkspaceService(db_session)

    unique_email = f"dev-{uuid.uuid4().hex[:8]}@atlas.io"
    profile = {
        "email": unique_email,
        "name": "Dev User",
        "avatar_url": "https://atlas.io/avatar.png",
        "scopes": ["openid", "email"],
    }

    user, oauth_acc, is_new = await identity_service.find_or_create_user_from_oauth(
        provider="google",
        provider_user_id=f"google_sub_{uuid.uuid4().hex[:8]}",
        provider_email=unique_email,
        profile_data=profile,
        access_token="google_access_token_abc",
    )

    assert is_new is True
    assert user.email == unique_email
    assert oauth_acc.provider == "google"

    # Provision workspace for new user
    org, ws, member = await ws_service.provision_personal_workspace(user)
    assert org.name == "Dev User's Org"
    assert ws.name == "Default Workspace"
    
    fetched_member = await ws_service.member_repo.get_membership(ws.id, user.id)
    assert fetched_member.role.name == "Owner"
