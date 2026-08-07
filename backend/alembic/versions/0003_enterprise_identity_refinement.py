"""Enterprise identity platform refinement

Revision ID: 0003_enterprise_identity
Revises: 0002_identity_platform
Create Date: 2026-08-07 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0003_enterprise_identity'
down_revision: Union[str, None] = '0002_identity_platform'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update oauth_accounts
    op.execute("ALTER TABLE oauth_accounts ADD COLUMN IF NOT EXISTS provider_username VARCHAR(255)")
    op.execute("ALTER TABLE oauth_accounts ADD COLUMN IF NOT EXISTS provider_avatar TEXT")

    # 2. Update organizations and workspaces
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active' NOT NULL")
    op.execute("ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active' NOT NULL")

    # 3. Clean slate for new refinement tables
    op.execute("DROP TABLE IF EXISTS audit_events CASCADE")
    op.execute("DROP TABLE IF EXISTS service_accounts CASCADE")
    op.execute("DROP TABLE IF EXISTS workspace_policies CASCADE")
    op.execute("DROP TABLE IF EXISTS workspace_configuration CASCADE")
    op.execute("DROP TABLE IF EXISTS workspace_settings CASCADE")
    op.execute("DROP TABLE IF EXISTS organization_members CASCADE")

    # 4. Create organization_members
    op.create_table(
        'organization_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='MEMBER'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('organization_id', 'user_id', name='uq_org_members_user')
    )
    op.create_index('ix_org_members_org_id', 'organization_members', ['organization_id'])
    op.create_index('ix_org_members_user_id', 'organization_members', ['user_id'])

    # 4. Migrate workspace_settings -> workspace_configuration
    op.execute("DROP TABLE IF EXISTS workspace_settings CASCADE")

    op.create_table(
        'workspace_configuration',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('timezone', sa.String(length=64), nullable=False, server_default='UTC'),
        sa.Column('branding', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('default_provider', sa.String(length=50), nullable=True),
        sa.Column('ai_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('notification_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )

    # 5. Create workspace_policies
    op.create_table(
        'workspace_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('require_mfa', sa.Boolean(), nullable=False, server_default='FALSE'),
        sa.Column('allow_guests', sa.Boolean(), nullable=False, server_default='TRUE'),
        sa.Column('allowed_integrations', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='365'),
        sa.Column('default_ai_provider', sa.String(length=50), nullable=False, server_default='gemini'),
        sa.Column('api_restrictions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )

    # 6. Create service_accounts
    op.create_table(
        'service_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_service_accounts_workspace_id', 'service_accounts', ['workspace_id'])
    op.create_index('ix_service_accounts_status', 'service_accounts', ['status'])

    # 7. Update api_keys table
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE SET NULL")
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS service_account_id UUID REFERENCES service_accounts(id) ON DELETE CASCADE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_user_id ON api_keys (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_service_account_id ON api_keys (service_account_id)")

    # 8. Create audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('actor_type', sa.String(length=30), nullable=False, server_default='user'),
        sa.Column('actor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('correlation_id', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
    )
    op.create_index('ix_audit_events_event_type', 'audit_events', ['event_type'])
    op.create_index('ix_audit_events_actor_id', 'audit_events', ['actor_id'])
    op.create_index('ix_audit_events_workspace_id', 'audit_events', ['workspace_id'])
    op.create_index('ix_audit_events_organization_id', 'audit_events', ['organization_id'])
    op.create_index('ix_audit_events_created_at', 'audit_events', ['created_at'])


def downgrade() -> None:
    pass
