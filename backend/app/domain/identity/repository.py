"""
Identity Domain Repositories.

Provides async database access methods for identity models.
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.identity.models import (
    ApiKey,
    OAuthAccount,
    RefreshToken,
    ServiceAccount,
    Session,
    User,
)


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = (
            select(User)
            .filter(User.id == user_id, User.deleted_at.is_(None))
            .options(selectinload(User.oauth_accounts))
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        normalized_email = email.lower().strip()
        stmt = (
            select(User)
            .filter(User.email == normalized_email, User.deleted_at.is_(None))
            .options(selectinload(User.oauth_accounts))
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def create(
        self,
        email: str,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        email_verified: bool = False,
        locale: str = "en",
        timezone_str: str = "UTC",
    ) -> User:
        user = User(
            email=email.lower().strip(),
            display_name=display_name,
            avatar_url=avatar_url,
            email_verified=email_verified,
            locale=locale,
            timezone=timezone_str,
            status="active",
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update(self, user: User) -> User:
        user.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return user

    async def soft_delete(self, user_id: UUID) -> bool:
        user = await self.get_by_id(user_id)
        if not user:
            return False
        user.soft_delete()
        await self.db.flush()
        return True


class OAuthAccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_provider_and_id(
        self, provider: str, provider_user_id: str
    ) -> Optional[OAuthAccount]:
        stmt = (
            select(OAuthAccount)
            .filter(
                OAuthAccount.provider == provider.lower(),
                OAuthAccount.provider_user_id == str(provider_user_id),
            )
            .options(selectinload(OAuthAccount.user))
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_by_user_id(self, user_id: UUID) -> List[OAuthAccount]:
        stmt = select(OAuthAccount).filter(OAuthAccount.user_id == user_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(
        self,
        user_id: UUID,
        provider: str,
        provider_user_id: str,
        provider_email: Optional[str] = None,
        provider_username: Optional[str] = None,
        provider_avatar: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        encrypted_access_token: Optional[str] = None,
        encrypted_refresh_token: Optional[str] = None,
        token_expires_at: Optional[datetime] = None,
        raw_profile: Optional[dict] = None,
    ) -> OAuthAccount:
        account = OAuthAccount(
            user_id=user_id,
            provider=provider.lower(),
            provider_user_id=str(provider_user_id),
            provider_email=provider_email.lower().strip() if provider_email else None,
            provider_username=provider_username,
            provider_avatar=provider_avatar,
            scopes=scopes or [],
            encrypted_access_token=encrypted_access_token,
            encrypted_refresh_token=encrypted_refresh_token,
            token_expires_at=token_expires_at,
            raw_profile=raw_profile or {},
        )
        self.db.add(account)
        await self.db.flush()
        return account

    async def delete(self, account_id: UUID) -> bool:
        stmt = select(OAuthAccount).filter(OAuthAccount.id == account_id)
        res = await self.db.execute(stmt)
        acc = res.scalars().first()
        if not acc:
            return False
        await self.db.delete(acc)
        await self.db.flush()
        return True


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, session_id: UUID) -> Optional[Session]:
        stmt = select(Session).filter(Session.id == session_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def create(
        self,
        user_id: UUID,
        expires_at: datetime,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Session:
        session = Session(
            user_id=user_id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def update_last_active(self, session_id: UUID) -> None:
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(last_active_at=datetime.now(timezone.utc))
        )
        await self.db.execute(stmt)

    async def revoke(self, session_id: UUID, reason: str = "logout") -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(is_active=False, revoked_at=now, revocation_reason=reason)
        )
        await self.db.execute(stmt)

    async def revoke_all_for_user(self, user_id: UUID, reason: str = "logout_all") -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.is_active.is_(True))
            .values(is_active=False, revoked_at=now, revocation_reason=reason)
        )
        await self.db.execute(stmt)


class RefreshTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        stmt = select(RefreshToken).filter(RefreshToken.token_hash == token_hash)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def create(
        self,
        session_id: UUID,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        token = RefreshToken(
            session_id=session_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def mark_used(self, token_id: UUID, replaced_by_id: Optional[UUID] = None) -> None:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(used_at=datetime.now(timezone.utc), replaced_by_id=replaced_by_id)
        )
        await self.db.execute(stmt)


class ServiceAccountRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, service_account_id: UUID) -> Optional[ServiceAccount]:
        stmt = (
            select(ServiceAccount)
            .filter(ServiceAccount.id == service_account_id)
            .options(selectinload(ServiceAccount.role))
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_by_workspace(self, workspace_id: UUID) -> List[ServiceAccount]:
        stmt = (
            select(ServiceAccount)
            .filter(ServiceAccount.workspace_id == workspace_id)
            .options(selectinload(ServiceAccount.role))
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(
        self,
        workspace_id: UUID,
        name: str,
        role_id: UUID,
        description: Optional[str] = None,
        created_by_user_id: Optional[UUID] = None,
    ) -> ServiceAccount:
        sa = ServiceAccount(
            workspace_id=workspace_id,
            name=name,
            role_id=role_id,
            description=description,
            created_by_user_id=created_by_user_id,
            status="active",
        )
        self.db.add(sa)
        await self.db.flush()
        return sa

    async def delete(self, service_account_id: UUID) -> bool:
        sa = await self.get_by_id(service_account_id)
        if not sa:
            return False
        await self.db.delete(sa)
        await self.db.flush()
        return True


class ApiKeyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_hash(self, key_hash: str) -> Optional[ApiKey]:
        stmt = (
            select(ApiKey)
            .filter(ApiKey.key_hash == key_hash, ApiKey.is_active.is_(True))
            .options(selectinload(ApiKey.user), selectinload(ApiKey.service_account))
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_by_workspace(self, workspace_id: UUID) -> List[ApiKey]:
        stmt = select(ApiKey).filter(
            ApiKey.workspace_id == workspace_id, ApiKey.is_active.is_(True)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(
        self,
        workspace_id: UUID,
        name: str,
        key_prefix: str,
        key_hash: str,
        user_id: Optional[UUID] = None,
        service_account_id: Optional[UUID] = None,
        description: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        expires_at: Optional[datetime] = None,
    ) -> ApiKey:
        api_key = ApiKey(
            workspace_id=workspace_id,
            user_id=user_id,
            service_account_id=service_account_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            description=description,
            scopes=scopes or [],
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(api_key)
        await self.db.flush()
        return api_key

    async def revoke(self, key_id: UUID, revoked_by_user_id: Optional[UUID]) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(is_active=False, revoked_at=now, revoked_by_user_id=revoked_by_user_id)
        )
        await self.db.execute(stmt)
