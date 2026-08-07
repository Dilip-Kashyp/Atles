"""
Identity Domain Services.

Contains business logic for:
- Identity management (User & OAuth account provisioning)
- Session lifecycle & token rotation
- Account linking & unlinking (Google, GitHub, Microsoft, Slack, Okta)
- Account merging (MergeAccountService for multi-email duplicate merging)
"""
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.service import AuditService
from app.domain.identity.models import OAuthAccount, Session, User
from app.domain.identity.repository import (
    OAuthAccountRepository,
    RefreshTokenRepository,
    SessionRepository,
    UserRepository,
)
from app.domain.shared.exceptions import (
    AccountAlreadyLinkedError,
    AuthenticationError,
    ExpiredTokenError,
    InvalidTokenError,
    OAuthError,
    TokenReuseDetectedError,
    UserNotFoundError,
    ValidationError,
)
from app.domain.workspace.models import OrganizationMember, WorkspaceMember
from app.infrastructure.security import encryption, hashing, tokens


class SessionService:
    """
    Manages server-side sessions and rotating refresh tokens.
    """
    REFRESH_TOKEN_EXPIRE_DAYS = 30

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.session_repo = SessionRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)

    async def create_session(
        self,
        user_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[Session, str, str]:
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
        session = await self.session_repo.create(
            user_id=user_id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        access_token = tokens.create_access_token(
            user_id=str(user_id), session_id=str(session.id)
        )

        raw_refresh_token = hashing.generate_secure_token(32)
        token_hash = hashing.hash_token(raw_refresh_token)

        await self.refresh_repo.create(
            session_id=session.id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        return session, access_token, raw_refresh_token

    async def rotate_refresh_token(
        self, raw_refresh_token: str
    ) -> tuple[str, str, UUID]:
        token_hash = hashing.hash_token(raw_refresh_token)
        token_record = await self.refresh_repo.get_by_hash(token_hash)

        if not token_record:
            raise InvalidTokenError("Invalid refresh token")

        if token_record.used_at is not None:
            await self.session_repo.revoke_all_for_user(
                token_record.user_id, reason="compromise_token_reuse"
            )
            raise TokenReuseDetectedError(
                "Refresh token reuse detected. All sessions revoked for security."
            )

        if token_record.revoked_at or token_record.expires_at < datetime.now(timezone.utc):
            raise ExpiredTokenError("Refresh token is expired or revoked")

        session = await self.session_repo.get_by_id(token_record.session_id)
        if not session or not session.is_active or session.expires_at < datetime.now(timezone.utc):
            raise AuthenticationError("Session is inactive or expired")

        raw_new_refresh = hashing.generate_secure_token(32)
        new_token_hash = hashing.hash_token(raw_new_refresh)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)

        new_token_record = await self.refresh_repo.create(
            session_id=session.id,
            user_id=token_record.user_id,
            token_hash=new_token_hash,
            expires_at=expires_at,
        )

        await self.refresh_repo.mark_used(token_record.id, replaced_by_id=new_token_record.id)
        await self.session_repo.update_last_active(session.id)

        new_access_token = tokens.create_access_token(
            user_id=str(token_record.user_id), session_id=str(session.id)
        )

        return new_access_token, raw_new_refresh, token_record.user_id

    async def logout_session(self, session_id: UUID) -> None:
        await self.session_repo.revoke(session_id, reason="logout")

    async def logout_all_sessions(self, user_id: UUID) -> None:
        await self.session_repo.revoke_all_for_user(user_id, reason="logout_all")


class IdentityService:
    """
    Core identity orchestrator.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.oauth_repo = OAuthAccountRepository(db)

    async def get_user_by_id(self, user_id: UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User with ID {user_id} not found")
        return user

    async def find_or_create_user_from_oauth(
        self,
        provider: str,
        provider_user_id: str,
        provider_email: str | None,
        profile_data: dict[str, Any],
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> tuple[User, OAuthAccount, bool]:
        oauth_account = await self.oauth_repo.get_by_provider_and_id(
            provider, provider_user_id
        )

        encrypted_access = encryption.encrypt(access_token) if access_token else None
        encrypted_refresh = encryption.encrypt(refresh_token) if refresh_token else None

        if oauth_account:
            await self.oauth_repo.db.execute(
                update(OAuthAccount)
                .where(OAuthAccount.id == oauth_account.id)
                .values(
                    encrypted_access_token=encrypted_access.hex() if encrypted_access else None,
                    encrypted_refresh_token=encrypted_refresh.hex() if encrypted_refresh else None,
                    provider_username=profile_data.get("username"),
                    provider_avatar=profile_data.get("avatar_url"),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            user = await self.user_repo.get_by_id(oauth_account.user_id)
            if not user:
                raise UserNotFoundError("Associated user account no longer exists")

            if profile_data.get("name") and not user.display_name:
                user.display_name = profile_data.get("name")
            if profile_data.get("avatar_url") and not user.avatar_url:
                user.avatar_url = profile_data.get("avatar_url")
            await self.user_repo.update(user)

            return user, oauth_account, False

        email = provider_email or profile_data.get("email")
        if not email:
            raise OAuthError(f"OAuth provider {provider} did not supply an email address")

        is_new_user = False
        user = await self.user_repo.get_by_email(email)

        if not user:
            is_new_user = True
            user = await self.user_repo.create(
                email=email,
                display_name=profile_data.get("name"),
                avatar_url=profile_data.get("avatar_url"),
                email_verified=True if provider in ["google", "github", "microsoft"] else False,
            )

        oauth_account = await self.oauth_repo.create(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=email,
            provider_username=profile_data.get("username"),
            provider_avatar=profile_data.get("avatar_url"),
            scopes=profile_data.get("scopes", []),
            encrypted_access_token=encrypted_access.hex() if encrypted_access else None,
            encrypted_refresh_token=encrypted_refresh.hex() if encrypted_refresh else None,
            raw_profile=profile_data,
        )

        return user, oauth_account, is_new_user


class AccountLinkingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.oauth_repo = OAuthAccountRepository(db)

    async def link_provider(
        self,
        user_id: UUID,
        provider: str,
        provider_user_id: str,
        provider_email: str | None,
        profile_data: dict[str, Any],
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> OAuthAccount:
        existing = await self.oauth_repo.get_by_provider_and_id(
            provider, provider_user_id
        )
        if existing:
            if existing.user_id != user_id:
                raise AccountAlreadyLinkedError(
                    f"This {provider} account is already linked to another Atlas user."
                )
            return existing

        encrypted_access = encryption.encrypt(access_token) if access_token else None
        encrypted_refresh = encryption.encrypt(refresh_token) if refresh_token else None

        oauth_account = await self.oauth_repo.create(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            provider_email=provider_email,
            provider_username=profile_data.get("username"),
            provider_avatar=profile_data.get("avatar_url"),
            scopes=profile_data.get("scopes", []),
            encrypted_access_token=encrypted_access.hex() if encrypted_access else None,
            encrypted_refresh_token=encrypted_refresh.hex() if encrypted_refresh else None,
            raw_profile=profile_data,
        )

        
        audit = AuditService(self.db)
        await audit.record_event(
            event_type="OAuthLinked",
            resource_type="oauth_account",
            actor_id=user_id,
            resource_id=oauth_account.id,
            payload={"provider": provider, "provider_user_id": provider_user_id},
        )

        return oauth_account

    async def unlink_provider(self, user_id: UUID, provider: str) -> bool:
        accounts = await self.oauth_repo.list_by_user_id(user_id)
        target = next((a for a in accounts if a.provider.lower() == provider.lower()), None)
        if not target:
            raise ValidationError(f"No linked {provider} account found for this user.")

        if len(accounts) <= 1:
            raise ValidationError(
                "Cannot unlink the only authentication provider for your account."
            )

        await self.oauth_repo.delete(target.id)

        audit = AuditService(self.db)
        await audit.record_event(
            event_type="OAuthUnlinked",
            resource_type="oauth_account",
            actor_id=user_id,
            payload={"provider": provider},
        )
        return True


class MergeAccountService:
    """
    Safely merges a secondary user account into a primary user account when duplicate accounts exist.
    Rebinds OAuth accounts, memberships, and credentials, then soft-deletes the secondary account.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    async def merge_accounts(
        self, primary_user_id: UUID, secondary_user_id: UUID, actor_user_id: UUID
    ) -> User:
        if primary_user_id == secondary_user_id:
            raise ValidationError("Primary and secondary user IDs must be different.")

        primary_user = await self.user_repo.get_by_id(primary_user_id)
        secondary_user = await self.user_repo.get_by_id(secondary_user_id)

        if not primary_user or not secondary_user:
            raise UserNotFoundError("One or both user accounts do not exist.")

        
        await self.db.execute(
            update(OAuthAccount)
            .where(OAuthAccount.user_id == secondary_user_id)
            .values(user_id=primary_user_id)
        )

        
        sec_org_mems_stmt = select(OrganizationMember).filter(
            OrganizationMember.user_id == secondary_user_id
        )
        res = await self.db.execute(sec_org_mems_stmt)
        sec_org_mems = list(res.scalars().all())

        for om in sec_org_mems:
            prim_om_stmt = select(OrganizationMember).filter(
                OrganizationMember.organization_id == om.organization_id,
                OrganizationMember.user_id == primary_user_id,
            )
            prim_om = (await self.db.execute(prim_om_stmt)).scalars().first()
            if not prim_om:
                om.user_id = primary_user_id
            else:
                await self.db.delete(om)

        
        sec_ws_mems_stmt = select(WorkspaceMember).filter(
            WorkspaceMember.user_id == secondary_user_id
        )
        res_ws = await self.db.execute(sec_ws_mems_stmt)
        sec_ws_mems = list(res_ws.scalars().all())

        for wm in sec_ws_mems:
            prim_wm_stmt = select(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == wm.workspace_id,
                WorkspaceMember.user_id == primary_user_id,
            )
            prim_wm = (await self.db.execute(prim_wm_stmt)).scalars().first()
            if not prim_wm:
                wm.user_id = primary_user_id
            else:
                await self.db.delete(wm)

        
        secondary_user.soft_delete()
        await self.db.flush()

        
        audit = AuditService(self.db)
        await audit.record_event(
            event_type="AccountMerged",
            resource_type="user",
            actor_id=actor_user_id,
            resource_id=primary_user_id,
            payload={
                "primary_user_id": str(primary_user_id),
                "merged_secondary_user_id": str(secondary_user_id),
            },
        )

        return primary_user
