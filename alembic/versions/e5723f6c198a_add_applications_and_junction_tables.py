"""add_applications_and_junction_tables

Revision ID: e5723f6c198a
Revises: 5e69f529b2dc
Create Date: 2025-12-14 19:57:44.516988

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e5723f6c198a'
down_revision: Union[str, Sequence[str], None] = '5e69f529b2dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add applications, project_applications, and control_applications tables."""
    
    # Create applications table (tenant-owned)
    op.create_table('applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('scope_rationale', sa.String(length=1000), nullable=True),
        sa.Column('business_owner_membership_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('it_owner_membership_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['business_owner_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['it_owner_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        comment='Applications are tenant-owned business applications'
    )
    op.create_index('ix_applications_tenant_id', 'applications', ['tenant_id'], unique=False)
    op.create_index('ix_applications_id', 'applications', ['id'], unique=False)
    op.create_index('ix_applications_business_owner_membership_id', 'applications', ['business_owner_membership_id'], unique=False)
    op.create_index('ix_applications_it_owner_membership_id', 'applications', ['it_owner_membership_id'], unique=False)
    # Composite index for tenant-scoped lookups
    op.create_index('ix_applications_tenant_id_id', 'applications', ['tenant_id', 'id'], unique=False)
    
    # Create project_applications join table (tenant-scoped)
    op.create_table('project_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'project_id', 'application_id', name='uq_project_application_tenant'),
        comment='Join table linking projects to applications with tenant isolation'
    )
    op.create_index('ix_project_applications_tenant_id', 'project_applications', ['tenant_id'], unique=False)
    op.create_index('ix_project_applications_project_id', 'project_applications', ['project_id'], unique=False)
    op.create_index('ix_project_applications_application_id', 'project_applications', ['application_id'], unique=False)
    op.create_index('ix_project_applications_id', 'project_applications', ['id'], unique=False)
    # Composite index for tenant-scoped lookups
    op.create_index('ix_project_applications_tenant_id_id', 'project_applications', ['tenant_id', 'id'], unique=False)
    
    # Create control_applications join table (tenant-scoped)
    op.create_table('control_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('control_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'control_id', 'application_id', name='uq_control_application_tenant'),
        comment='Join table linking controls to applications with tenant isolation'
    )
    op.create_index('ix_control_applications_tenant_id', 'control_applications', ['tenant_id'], unique=False)
    op.create_index('ix_control_applications_control_id', 'control_applications', ['control_id'], unique=False)
    op.create_index('ix_control_applications_application_id', 'control_applications', ['application_id'], unique=False)
    op.create_index('ix_control_applications_id', 'control_applications', ['id'], unique=False)
    # Composite index for tenant-scoped lookups
    op.create_index('ix_control_applications_tenant_id_id', 'control_applications', ['tenant_id', 'id'], unique=False)


def downgrade() -> None:
    """Remove applications, project_applications, and control_applications tables."""
    
    # Drop control_applications table
    op.drop_index('ix_control_applications_tenant_id_id', table_name='control_applications')
    op.drop_index('ix_control_applications_id', table_name='control_applications')
    op.drop_index('ix_control_applications_application_id', table_name='control_applications')
    op.drop_index('ix_control_applications_control_id', table_name='control_applications')
    op.drop_index('ix_control_applications_tenant_id', table_name='control_applications')
    op.drop_table('control_applications')
    
    # Drop project_applications table
    op.drop_index('ix_project_applications_tenant_id_id', table_name='project_applications')
    op.drop_index('ix_project_applications_id', table_name='project_applications')
    op.drop_index('ix_project_applications_application_id', table_name='project_applications')
    op.drop_index('ix_project_applications_project_id', table_name='project_applications')
    op.drop_index('ix_project_applications_tenant_id', table_name='project_applications')
    op.drop_table('project_applications')
    
    # Drop applications table
    op.drop_index('ix_applications_tenant_id_id', table_name='applications')
    op.drop_index('ix_applications_it_owner_membership_id', table_name='applications')
    op.drop_index('ix_applications_business_owner_membership_id', table_name='applications')
    op.drop_index('ix_applications_id', table_name='applications')
    op.drop_index('ix_applications_tenant_id', table_name='applications')
    op.drop_table('applications')
