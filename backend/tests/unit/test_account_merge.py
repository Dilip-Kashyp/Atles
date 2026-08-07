"""Unit & Integration tests for MergeAccountService."""
import uuid
import pytest
from app.domain.identity.repository import UserRepository, OAuthAccountRepository
from app.domain.identity.services import MergeAccountService


@pytest.mark.asyncio
async def test_account_merge(db_session):
    user_repo = UserRepository(db_session)
    oauth_repo = OAuthAccountRepository(db_session)
    merge_service = MergeAccountService(db_session)

    u1_email = f"user1-{uuid.uuid4().hex[:8]}@atlas.io"
    u2_email = f"user2-{uuid.uuid4().hex[:8]}@atlas.io"

    user1 = await user_repo.create(email=u1_email, display_name="User One")
    user2 = await user_repo.create(email=u2_email, display_name="User Two")

    # Link google to user1, github to user2
    acc1 = await oauth_repo.create(user_id=user1.id, provider="google", provider_user_id=f"g_{uuid.uuid4().hex[:8]}")
    acc2 = await oauth_repo.create(user_id=user2.id, provider="github", provider_user_id=f"gh_{uuid.uuid4().hex[:8]}")

    # Merge user2 into user1
    merged = await merge_service.merge_accounts(primary_user_id=user1.id, secondary_user_id=user2.id, actor_user_id=user1.id)

    assert merged.id == user1.id
    user2_reloaded = await user_repo.get_by_id(user2.id)
    assert user2_reloaded is None  # soft deleted

    # Verify user1 now has both OAuth accounts
    user1_accs = await oauth_repo.list_by_user_id(user1.id)
    providers = [a.provider for a in user1_accs]
    assert "google" in providers
    assert "github" in providers
