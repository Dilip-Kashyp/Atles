"""
Workspace Domain Services.

Contains business logic for:
- Organization & Organization Member governance
- Workspace & Workspace Configuration provisioning
- Workspace Security Policies management
- Service Account lifecycle management
- Workspace RBAC & Member invitations
"""
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.service import AuditService
from app.domain.identity.models import ServiceAccount, User
from app.domain.identity.repository import ServiceAccountRepository
from app.domain.shared.exceptions import (
    AlreadyMemberError,
    InsufficientPermissionsError,
    InvitationAlreadyAcceptedError,
    InvitationExpiredError,
    InvitationNotFoundError,
    OrganizationNotFoundError,
    ValidationError,
    WorkspaceMembershipRequiredError,
    WorkspaceNotFoundError,
)
from app.domain.workspace.models import (
    Organization,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspacePolicy,
)
from app.domain.workspace.repository import (
    InviteRepository,
    MemberRepository,
    OrganizationRepository,
    OrgMemberRepository,
    PolicyRepository,
    RoleRepository,
    WorkspaceRepository,
)
from app.infrastructure.security import hashing


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-") or "workspace"


class RBACService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.member_repo = MemberRepository(db)
        self.role_repo = RoleRepository(db)

    async def get_user_permissions(
        self, workspace_id: UUID, user_id: UUID
    ) -> set[str]:
        member = await self.member_repo.get_membership(workspace_id, user_id)
        if not member or not member.role:
            return set()

        permissions = set()
        for rp in member.role.role_permissions:
            if rp.permission:
                permissions.add(rp.permission.name)
        return permissions

    async def has_permission(
        self, workspace_id: UUID, user_id: UUID, required_permission: str
    ) -> bool:
        perms = await self.get_user_permissions(workspace_id, user_id)
        return required_permission in perms

    async def require_permission(
        self, workspace_id: UUID, user_id: UUID, required_permission: str
    ) -> None:
        member = await self.member_repo.get_membership(workspace_id, user_id)
        if not member:
            raise WorkspaceMembershipRequiredError(
                f"User {user_id} is not a member of workspace {workspace_id}"
            )

        has_perm = await self.has_permission(workspace_id, user_id, required_permission)
        if not has_perm:
            raise InsufficientPermissionsError(required_permission)


class PolicyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.policy_repo = PolicyRepository(db)

    async def get_policy(self, workspace_id: UUID) -> WorkspacePolicy:
        policy = await self.policy_repo.get_by_workspace(workspace_id)
        if not policy:
            policy = await self.policy_repo.update_policy(workspace_id)
        return policy

    async def update_policy(
        self,
        workspace_id: UUID,
        require_mfa: bool | None = None,
        allow_guests: bool | None = None,
        allowed_integrations: list[str] | None = None,
        retention_days: int | None = None,
        default_ai_provider: str | None = None,
        api_restrictions: dict | None = None,
        actor_id: UUID | None = None,
    ) -> WorkspacePolicy:
        updated = await self.policy_repo.update_policy(
            workspace_id=workspace_id,
            require_mfa=require_mfa,
            allow_guests=allow_guests,
            allowed_integrations=allowed_integrations,
            retention_days=retention_days,
            default_ai_provider=default_ai_provider,
            api_restrictions=api_restrictions,
        )

        audit = AuditService(self.db)
        await audit.record_event(
            event_type="PolicyUpdated",
            resource_type="workspace_policy",
            workspace_id=workspace_id,
            actor_id=actor_id,
            resource_id=updated.id,
        )
        return updated


class OrganizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.org_mem_repo = OrgMemberRepository(db)

    async def create_organization(
        self,
        name: str,
        creator_user_id: UUID | None = None,
        slug: str | None = None,
        logo_url: str | None = None,
        billing_email: str | None = None,
    ) -> Organization:
        org_slug = slugify(slug or name)
        existing = await self.org_repo.get_by_slug(org_slug)
        if existing:
            org_slug = f"{org_slug}-{hashing.generate_secure_token(4).lower()}"

        org = await self.org_repo.create(
            name=name,
            slug=org_slug,
            logo_url=logo_url,
            billing_email=billing_email,
        )

        if creator_user_id:
            await self.org_mem_repo.add_member(
                org_id=org.id, user_id=creator_user_id, role="OWNER"
            )

        audit = AuditService(self.db)
        await audit.record_event(
            event_type="OrganizationCreated",
            resource_type="organization",
            organization_id=org.id,
            actor_id=creator_user_id,
            resource_id=org.id,
            payload={"name": org.name, "slug": org.slug},
        )

        return org

    async def get_by_id(self, org_id: UUID) -> Organization:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise OrganizationNotFoundError(f"Organization {org_id} not found")
        return org


class WorkspaceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.ws_repo = WorkspaceRepository(db)
        self.role_repo = RoleRepository(db)
        self.member_repo = MemberRepository(db)
        self.org_service = OrganizationService(db)

    async def provision_personal_workspace(self, user: User) -> tuple[Organization, Workspace, WorkspaceMember]:
        await self.role_repo.seed_system_roles_and_permissions()

        org_name = f"{user.display_name or 'Personal'}'s Org"
        org = await self.org_service.create_organization(
            name=org_name, creator_user_id=user.id
        )

        ws_slug = "default"
        ws = await self.ws_repo.create(
            org_id=org.id,
            name="Default Workspace",
            slug=ws_slug,
            is_default=True,
        )

        owner_role = await self.role_repo.get_by_name("Owner")
        if not owner_role:
            raise RuntimeError("Owner system role missing — seeding failed")

        member = await self.member_repo.create(
            workspace_id=ws.id,
            user_id=user.id,
            role_id=owner_role.id,
        )

        audit = AuditService(self.db)
        await audit.record_event(
            event_type="WorkspaceCreated",
            resource_type="workspace",
            workspace_id=ws.id,
            organization_id=org.id,
            actor_id=user.id,
            resource_id=ws.id,
            payload={"name": ws.name, "is_default": True},
        )

        return org, ws, member

    async def create_workspace(
        self,
        creator_user_id: UUID,
        name: str,
        org_id: UUID | None = None,
        slug: str | None = None,
        icon_url: str | None = None,
    ) -> tuple[Workspace, WorkspaceMember]:
        if not org_id:
            existing_ws = await self.ws_repo.list_by_user_id(creator_user_id)
            if existing_ws:
                org_id = existing_ws[0].org_id
            else:
                org = await self.org_service.create_organization(
                    name=f"{name} Org", creator_user_id=creator_user_id
                )
                org_id = org.id

        ws_slug = slugify(slug or name)
        existing_ws = await self.ws_repo.get_by_org_and_slug(org_id, ws_slug)
        if existing_ws:
            ws_slug = f"{ws_slug}-{hashing.generate_secure_token(4).lower()}"

        workspace = await self.ws_repo.create(
            org_id=org_id,
            name=name,
            slug=ws_slug,
            icon_url=icon_url,
        )

        owner_role = await self.role_repo.get_by_name("Owner")
        member = await self.member_repo.create(
            workspace_id=workspace.id,
            user_id=creator_user_id,
            role_id=owner_role.id,
        )

        audit = AuditService(self.db)
        await audit.record_event(
            event_type="WorkspaceCreated",
            resource_type="workspace",
            workspace_id=workspace.id,
            organization_id=org_id,
            actor_id=creator_user_id,
            resource_id=workspace.id,
            payload={"name": workspace.name},
        )

        return workspace, member

    async def get_workspace_by_id(self, workspace_id: UUID) -> Workspace:
        ws = await self.ws_repo.get_by_id(workspace_id)
        if not ws:
            raise WorkspaceNotFoundError(f"Workspace {workspace_id} not found")
        return ws

    async def list_user_workspaces(self, user_id: UUID) -> list[Workspace]:
        return await self.ws_repo.list_by_user_id(user_id)


class ServiceAccountService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sa_repo = ServiceAccountRepository(db)
        self.role_repo = RoleRepository(db)

    async def create_service_account(
        self,
        workspace_id: UUID,
        name: str,
        role_name: str = "Developer",
        description: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> ServiceAccount:
        role = await self.role_repo.get_by_name(role_name, workspace_id)
        if not role:
            raise ValidationError(f"Role '{role_name}' does not exist.")

        sa = await self.sa_repo.create(
            workspace_id=workspace_id,
            name=name,
            role_id=role.id,
            description=description,
            created_by_user_id=created_by_user_id,
        )

        audit = AuditService(self.db)
        await audit.record_event(
            event_type="ServiceAccountCreated",
            resource_type="service_account",
            workspace_id=workspace_id,
            actor_id=created_by_user_id,
            resource_id=sa.id,
            payload={"name": sa.name, "role": role.name},
        )
        return sa


class InviteService:
    INVITE_EXPIRE_DAYS = 7

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.invite_repo = InviteRepository(db)
        self.member_repo = MemberRepository(db)
        self.role_repo = RoleRepository(db)

    async def create_invitation(
        self,
        workspace_id: UUID,
        invited_by_user_id: UUID,
        email: str,
        role_id: UUID | None = None,
        role_name: str | None = "Developer",
    ) -> tuple[WorkspaceInvitation, str]:
        if not role_id:
            role = await self.role_repo.get_by_name(role_name or "Developer", workspace_id)
            if not role:
                raise ValidationError(f"Role {role_name} does not exist")
            role_id = role.id

        raw_token = hashing.generate_secure_token(32)
        token_hash = hashing.hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.INVITE_EXPIRE_DAYS)

        invite = await self.invite_repo.create(
            workspace_id=workspace_id,
            invited_by_user_id=invited_by_user_id,
            email=email,
            role_id=role_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        audit = AuditService(self.db)
        await audit.record_event(
            event_type="MemberInvited",
            resource_type="workspace_invitation",
            workspace_id=workspace_id,
            actor_id=invited_by_user_id,
            resource_id=invite.id,
            payload={"email": email},
        )

        return invite, raw_token

    async def accept_invitation(
        self, raw_token: str, accepting_user: User
    ) -> WorkspaceMember:
        token_hash = hashing.hash_token(raw_token)
        invite = await self.invite_repo.get_by_token_hash(token_hash)

        if not invite:
            raise InvitationNotFoundError("Invalid or expired invitation token")

        if invite.status == "accepted":
            raise InvitationAlreadyAcceptedError("Invitation has already been accepted")
        if invite.status == "revoked":
            raise InvitationRevokedError("Invitation has been revoked")
        if invite.expires_at < datetime.now(timezone.utc):
            raise InvitationExpiredError("Invitation token has expired")

        existing_member = await self.member_repo.get_membership(
            invite.workspace_id, accepting_user.id
        )
        if existing_member:
            await self.invite_repo.mark_accepted(invite.id, accepting_user.id)
            raise AlreadyMemberError("User is already a member of this workspace")

        member = await self.member_repo.create(
            workspace_id=invite.workspace_id,
            user_id=accepting_user.id,
            role_id=invite.role_id,
        )

        await self.invite_repo.mark_accepted(invite.id, accepting_user.id)

        audit = AuditService(self.db)
        await audit.record_event(
            event_type="InvitationAccepted",
            resource_type="workspace_member",
            workspace_id=invite.workspace_id,
            actor_id=accepting_user.id,
            resource_id=member.id,
        )

        return member
