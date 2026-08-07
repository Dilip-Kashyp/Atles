"""
Workspace Domain Repositories.

Provides async database access for organizations, org members, workspaces, configuration, policies, RBAC, members, and invitations.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.workspace.models import (
    Organization,
    OrganizationMember,
    Permission,
    Role,
    RolePermission,
    Workspace,
    WorkspaceConfiguration,
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspacePolicy,
)
from app.infrastructure.database.errors import handle_db_errors


class OrganizationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, org_id: UUID) -> Organization | None:
        stmt = (
            select(Organization)
            .filter(Organization.id == org_id, Organization.deleted_at.is_(None))
            .options(selectinload(Organization.workspaces), selectinload(Organization.domains))
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_by_slug(self, slug: str) -> Organization | None:
        stmt = select(Organization).filter(
            Organization.slug == slug.lower().strip(),
            Organization.deleted_at.is_(None),
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    @handle_db_errors
    async def create(
        self,
        name: str,
        slug: str,
        logo_url: str | None = None,
        billing_email: str | None = None,
    ) -> Organization:
        org = Organization(
            name=name,
            slug=slug.lower().strip(),
            logo_url=logo_url,
            billing_email=billing_email.lower().strip() if billing_email else None,
            status="active",
        )
        self.db.add(org)
        await self.db.flush()
        return org

    async def update(self, org: Organization) -> Organization:
        org.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return org


class OrgMemberRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_membership(
        self, org_id: UUID, user_id: UUID
    ) -> OrganizationMember | None:
        stmt = (
            select(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
            .options(selectinload(OrganizationMember.user))
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_by_org(self, org_id: UUID) -> list[OrganizationMember]:
        stmt = (
            select(OrganizationMember)
            .filter(OrganizationMember.organization_id == org_id)
            .options(selectinload(OrganizationMember.user))
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def add_member(
        self, org_id: UUID, user_id: UUID, role: str = "MEMBER"
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=org_id,
            user_id=user_id,
            role=role.upper(),
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def remove_member(self, org_id: UUID, user_id: UUID) -> bool:
        stmt = select(OrganizationMember).filter(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == user_id,
        )
        res = await self.db.execute(stmt)
        mem = res.scalars().first()
        if not mem:
            return False
        await self.db.delete(mem)
        await self.db.flush()
        return True


class WorkspaceRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, workspace_id: UUID) -> Workspace | None:
        stmt = (
            select(Workspace)
            .filter(Workspace.id == workspace_id, Workspace.deleted_at.is_(None))
            .options(
                selectinload(Workspace.organization),
                selectinload(Workspace.configuration),
                selectinload(Workspace.policy),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_by_org_and_slug(self, org_id: UUID, slug: str) -> Workspace | None:
        stmt = select(Workspace).filter(
            Workspace.org_id == org_id,
            Workspace.slug == slug.lower().strip(),
            Workspace.deleted_at.is_(None),
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_by_user_id(self, user_id: UUID) -> list[Workspace]:
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
            .filter(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "active",
                Workspace.deleted_at.is_(None),
            )
            .options(
                selectinload(Workspace.organization),
                selectinload(Workspace.configuration),
                selectinload(Workspace.policy),
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(
        self,
        org_id: UUID,
        name: str,
        slug: str,
        icon_url: str | None = None,
        is_default: bool = False,
    ) -> Workspace:
        ws = Workspace(
            org_id=org_id,
            name=name,
            slug=slug.lower().strip(),
            icon_url=icon_url,
            is_default=is_default,
            status="active",
        )
        self.db.add(ws)
        await self.db.flush()

        
        config = WorkspaceConfiguration(workspace_id=ws.id)
        policy = WorkspacePolicy(workspace_id=ws.id)
        self.db.add(config)
        self.db.add(policy)
        await self.db.flush()

        return ws

    @handle_db_errors
    async def update(self, workspace: Workspace) -> Workspace:
        workspace.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return workspace


class PolicyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_workspace(self, workspace_id: UUID) -> WorkspacePolicy | None:
        stmt = select(WorkspacePolicy).filter(WorkspacePolicy.workspace_id == workspace_id)
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def update_policy(
        self,
        workspace_id: UUID,
        require_mfa: bool | None = None,
        allow_guests: bool | None = None,
        allowed_integrations: list[str] | None = None,
        retention_days: int | None = None,
        default_ai_provider: str | None = None,
        api_restrictions: dict | None = None,
    ) -> WorkspacePolicy:
        policy = await self.get_by_workspace(workspace_id)
        if not policy:
            policy = WorkspacePolicy(workspace_id=workspace_id)
            self.db.add(policy)

        if require_mfa is not None:
            policy.require_mfa = require_mfa
        if allow_guests is not None:
            policy.allow_guests = allow_guests
        if allowed_integrations is not None:
            policy.allowed_integrations = allowed_integrations
        if retention_days is not None:
            policy.retention_days = retention_days
        if default_ai_provider is not None:
            policy.default_ai_provider = default_ai_provider
        if api_restrictions is not None:
            policy.api_restrictions = api_restrictions

        policy.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return policy


class RoleRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, role_id: UUID) -> Role | None:
        stmt = (
            select(Role)
            .filter(Role.id == role_id)
            .options(
                selectinload(Role.role_permissions).selectinload(RolePermission.permission)
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def get_by_name(
        self, name: str, workspace_id: UUID | None = None
    ) -> Role | None:
        stmt = (
            select(Role)
            .filter(
                Role.name == name,
                (Role.workspace_id == workspace_id) | (Role.workspace_id.is_(None)),
            )
            .options(
                selectinload(Role.role_permissions).selectinload(RolePermission.permission)
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_available_for_workspace(self, workspace_id: UUID) -> list[Role]:
        stmt = (
            select(Role)
            .filter((Role.workspace_id == workspace_id) | (Role.workspace_id.is_(None)))
            .options(
                selectinload(Role.role_permissions).selectinload(RolePermission.permission)
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def seed_system_roles_and_permissions(self) -> None:
        permissions_data = [
            ("workspace:read", "workspace", "View workspace details"),
            ("workspace:write", "workspace", "Modify workspace settings"),
            ("workspace:delete", "workspace", "Delete workspace"),
            ("member:read", "member", "List workspace members"),
            ("member:invite", "member", "Invite members"),
            ("member:manage", "member", "Change roles or remove members"),
            ("role:read", "role", "List roles and permissions"),
            ("role:manage", "role", "Create and edit custom roles"),
            ("api_key:manage", "identity", "Manage API keys"),
            ("service_account:manage", "identity", "Manage Service Accounts"),
            ("policy:manage", "workspace", "Manage workspace security policies"),
            ("integration:connect", "integration", "Connect third-party integrations"),
            ("workflow:execute", "workflow", "Execute workflows"),
        ]

        perm_map = {}
        for p_name, p_domain, p_desc in permissions_data:
            stmt = select(Permission).filter(Permission.name == p_name)
            res = await self.db.execute(stmt)
            perm = res.scalars().first()
            if not perm:
                perm = Permission(name=p_name, domain=p_domain, description=p_desc)
                self.db.add(perm)
                await self.db.flush()
            perm_map[p_name] = perm

        roles_config = {
            "Owner": list(perm_map.keys()),
            "Admin": [p for p in perm_map if p != "workspace:delete"],
            "Manager": [
                "workspace:read",
                "member:read",
                "member:invite",
                "role:read",
                "integration:connect",
                "workflow:execute",
            ],
            "Developer": [
                "workspace:read",
                "member:read",
                "role:read",
                "api_key:manage",
                "integration:connect",
                "workflow:execute",
            ],
            "Viewer": ["workspace:read", "member:read", "role:read"],
        }

        for r_name, p_names in roles_config.items():
            stmt = select(Role).filter(Role.name == r_name, Role.workspace_id.is_(None))
            res = await self.db.execute(stmt)
            role = res.scalars().first()
            if not role:
                role = Role(
                    name=r_name,
                    description=f"System role: {r_name}",
                    is_system=True,
                    workspace_id=None,
                )
                self.db.add(role)
                await self.db.flush()

            for p_name in p_names:
                perm = perm_map[p_name]
                rp_stmt = select(RolePermission).filter(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm.id,
                )
                rp_res = await self.db.execute(rp_stmt)
                if not rp_res.scalars().first():
                    self.db.add(RolePermission(role_id=role.id, permission_id=perm.id))


class MemberRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_membership(
        self, workspace_id: UUID, user_id: UUID
    ) -> WorkspaceMember | None:
        stmt = (
            select(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.status == "active",
            )
            .options(
                selectinload(WorkspaceMember.user),
                selectinload(WorkspaceMember.role).selectinload(Role.role_permissions).selectinload(RolePermission.permission),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def list_by_workspace_id(self, workspace_id: UUID) -> list[WorkspaceMember]:
        stmt = (
            select(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.status == "active",
            )
            .options(
                selectinload(WorkspaceMember.user),
                selectinload(WorkspaceMember.role),
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def create(
        self, workspace_id: UUID, user_id: UUID, role_id: UUID
    ) -> WorkspaceMember:
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role_id=role_id,
            status="active",
        )
        self.db.add(member)
        await self.db.flush()
        return member

    async def remove(self, workspace_id: UUID, user_id: UUID) -> bool:
        stmt = (
            update(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
            .values(status="removed", updated_at=datetime.now(timezone.utc))
        )
        res = await self.db.execute(stmt)
        return res.rowcount > 0


class InviteRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_token_hash(self, token_hash: str) -> WorkspaceInvitation | None:
        stmt = (
            select(WorkspaceInvitation)
            .filter(WorkspaceInvitation.token_hash == token_hash)
            .options(
                selectinload(WorkspaceInvitation.workspace),
                selectinload(WorkspaceInvitation.role),
            )
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def create(
        self,
        workspace_id: UUID,
        invited_by_user_id: UUID,
        email: str,
        role_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> WorkspaceInvitation:
        invite = WorkspaceInvitation(
            workspace_id=workspace_id,
            invited_by_user_id=invited_by_user_id,
            email=email.lower().strip(),
            role_id=role_id,
            token_hash=token_hash,
            expires_at=expires_at,
            status="pending",
        )
        self.db.add(invite)
        await self.db.flush()
        return invite

    async def mark_accepted(
        self, invitation_id: UUID, accepted_by_user_id: UUID
    ) -> None:
        stmt = (
            update(WorkspaceInvitation)
            .where(WorkspaceInvitation.id == invitation_id)
            .values(
                status="accepted",
                accepted_at=datetime.now(timezone.utc),
                accepted_by_user_id=accepted_by_user_id,
            )
        )
        await self.db.execute(stmt)
