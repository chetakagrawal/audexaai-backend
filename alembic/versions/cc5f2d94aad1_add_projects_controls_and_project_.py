"""add projects controls and project_controls tables with tenant_id

Revision ID: cc5f2d94aad1
Revises: 561e7141f5cf
Create Date: 2025-12-13 10:35:07.808415

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'cc5f2d94aad1'
down_revision: Union[str, Sequence[str], None] = '561e7141f5cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add projects, controls, and project_controls tables with tenant_id."""
    
    # Create projects table (tenant-owned)
    op.create_table('projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('period_start', sa.Date(), nullable=True),
        sa.Column('period_end', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Projects are tenant-owned audit engagements'
    )
    op.create_index('ix_projects_tenant_id', 'projects', ['tenant_id'], unique=False)
    op.create_index('ix_projects_id', 'projects', ['id'], unique=False)
    # Composite index for tenant-scoped lookups
    op.create_index('ix_projects_tenant_id_id', 'projects', ['tenant_id', 'id'], unique=False)
    
    # Create controls table (tenant-owned)
    op.create_table('controls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('control_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('risk_rating', sa.String(length=50), nullable=True),
        sa.Column('control_type', sa.String(length=50), nullable=True),
        sa.Column('frequency', sa.String(length=50), nullable=True),
        sa.Column('is_key', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_automated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Controls are tenant-owned SOX controls'
    )
    op.create_index('ix_controls_tenant_id', 'controls', ['tenant_id'], unique=False)
    op.create_index('ix_controls_id', 'controls', ['id'], unique=False)
    # Composite index for tenant-scoped lookups
    op.create_index('ix_controls_tenant_id_id', 'controls', ['tenant_id', 'id'], unique=False)
    # Composite unique constraint: control_code must be unique per tenant
    op.create_unique_constraint('uq_controls_tenant_id_control_code', 'controls', ['tenant_id', 'control_code'])
    
    # Create project_controls join table (tenant-scoped)
    op.create_table('project_controls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('control_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_key_override', sa.Boolean(), nullable=True),
        sa.Column('frequency_override', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'project_id', 'control_id', name='uq_project_control_tenant'),
        comment='Join table linking projects to controls with tenant isolation'
    )
    op.create_index('ix_project_controls_tenant_id', 'project_controls', ['tenant_id'], unique=False)
    op.create_index('ix_project_controls_project_id', 'project_controls', ['project_id'], unique=False)
    op.create_index('ix_project_controls_control_id', 'project_controls', ['control_id'], unique=False)
    op.create_index('ix_project_controls_id', 'project_controls', ['id'], unique=False)
    # Composite index for tenant-scoped lookups
    op.create_index('ix_project_controls_tenant_id_id', 'project_controls', ['tenant_id', 'id'], unique=False)


def downgrade() -> None:
    """Remove projects, controls, and project_controls tables."""
    op.drop_index('ix_project_controls_tenant_id_id', table_name='project_controls')
    op.drop_index('ix_project_controls_id', table_name='project_controls')
    op.drop_index('ix_project_controls_control_id', table_name='project_controls')
    op.drop_index('ix_project_controls_project_id', table_name='project_controls')
    op.drop_index('ix_project_controls_tenant_id', table_name='project_controls')
    op.drop_table('project_controls')
    
    op.drop_constraint('uq_controls_tenant_id_control_code', 'controls', type_='unique')
    op.drop_index('ix_controls_tenant_id_id', table_name='controls')
    op.drop_index('ix_controls_id', table_name='controls')
    op.drop_index('ix_controls_tenant_id', table_name='controls')
    op.drop_table('controls')
    
    op.drop_index('ix_projects_tenant_id_id', table_name='projects')
    op.drop_index('ix_projects_id', table_name='projects')
    op.drop_index('ix_projects_tenant_id', table_name='projects')
    op.drop_table('projects')
