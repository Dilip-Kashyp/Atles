"""Integration tests for Service Accounts and Service Account API Keys."""
import uuid
import pytest
from app.domain.identity.repository import ApiKeyRepository, UserRepository
from app.domain.workspace.repository import RoleRepository
from app.domain.workspace.services import ServiceAccountService, WorkspaceService
from app.infrastructure.security import hashing


@pytest.mark.asyncio
async def test_service_account_and_api_key(db_session):
    user_repo = UserRepository(db_session)
    ws_service = WorkspaceService(db_session)
    sa_service = ServiceAccountService(db_session)
    api_key_repo = ApiKeyRepository(db_session)
    role_repo = RoleRepository(db_session)

    await role_repo.seed_system_roles_and_permissions()

    owner = await user_repo.create(email=f"owner-{uuid.uuid4().hex[:8]}@acme.com")
    workspace, _ = await ws_service.create_workspace(creator_user_id=owner.id, name="Automation WS")

    # Create Service Account
    sa = await sa_service.create_service_account(
        workspace_id=workspace.id,
        name="GitHub Bot",
        role_name="Developer",
        created_by_user_id=owner.id,
    )

    assert sa.name == "GitHub Bot"
    assert sa.workspace_id == workspace.id

    # Create API Key bound to Service Account
    raw_key = f"atls_bot_{hashing.generate_secure_token(32)}"
    key_hash = hashing.hash_token(raw_key)

    api_key = await api_key_repo.create(
        workspace_id=workspace.id,
        service_account_id=sa.id,
        name="Bot CI Key",
        key_prefix="atls_bot",
        key_hash=key_hash,
    )

    assert api_key.service_account_id == sa.id
    assert api_key.user_id is None

    # Lookup API key by hash
    fetched_key = await api_key_repo.get_by_hash(key_hash)
    assert fetched_key is not None
    assert fetched_key.service_account.name == "GitHub Bot"
