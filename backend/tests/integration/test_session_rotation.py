"""Integration tests for session lifecycle, refresh token rotation, and reuse detection."""
import pytest
from app.domain.identity.repository import UserRepository
from app.domain.identity.services import SessionService
from app.domain.shared.exceptions import TokenReuseDetectedError


@pytest.mark.asyncio
async def test_session_creation_and_rotation(db_session):
    import uuid
    user_repo = UserRepository(db_session)
    session_service = SessionService(db_session)

    unique_email = f"tester-{uuid.uuid4().hex[:8]}@atlas.io"
    user = await user_repo.create(email=unique_email, display_name="Tester")
    session, access_token, refresh_token = await session_service.create_session(user.id)

    assert session.is_active is True
    assert access_token is not None
    assert refresh_token is not None

    # Rotate refresh token
    new_access, new_refresh, u_id = await session_service.rotate_refresh_token(refresh_token)
    assert new_access is not None
    assert new_refresh != refresh_token
    assert u_id == user.id

    # REUSE DETECTION: Re-presenting old refresh_token must fail and revoke sessions
    with pytest.raises(TokenReuseDetectedError):
        await session_service.rotate_refresh_token(refresh_token)

    # Verify session is revoked
    updated_session = await session_service.session_repo.get_by_id(session.id)
    assert updated_session.is_active is False
    assert updated_session.revocation_reason == "compromise_token_reuse"
