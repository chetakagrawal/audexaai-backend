"""add_project_control_applications_table

Revision ID: e88d93747af
Revises: 5488bccb5e13
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e88d93747af'
down_revision: Union[str, Sequence[str], None] = '5488bccb5e13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create project_control_applications table with indexes and constraints."""
    
    # Create table
    op.create_table(
        'project_control_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_control_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_version_num', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False, server_default='manual'),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('added_by_membership_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('removed_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_control_id'], ['project_controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['added_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['removed_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
    )
    
    # Create indexes
    op.create_index('ix_project_control_applications_id', 'project_control_applications', ['id'])
    op.create_index('ix_project_control_applications_tenant_id', 'project_control_applications', ['tenant_id'])
    op.create_index('ix_project_control_applications_project_control_id', 'project_control_applications', ['project_control_id'])
    op.create_index('ix_project_control_applications_application_id', 'project_control_applications', ['application_id'])
    op.create_index('ix_project_control_applications_added_by_membership_id', 'project_control_applications', ['added_by_membership_id'])
    op.create_index('ix_project_control_applications_removed_at', 'project_control_applications', ['removed_at'])
    op.create_index('ix_pca_tenant_project_control', 'project_control_applications', ['tenant_id', 'project_control_id'])
    op.create_index('ix_pca_tenant_application', 'project_control_applications', ['tenant_id', 'application_id'])
    
    # Create partial unique index for active records only
    op.execute("""
        CREATE UNIQUE INDEX ux_project_control_apps_active 
        ON project_control_applications (tenant_id, project_control_id, application_id) 
        WHERE removed_at IS NULL
    """)


def downgrade() -> None:
    """Drop project_control_applications table."""
    
    # Drop indexes
    op.execute('DROP INDEX IF EXISTS ux_project_control_apps_active')
    op.drop_index('ix_pca_tenant_application', table_name='project_control_applications')
    op.drop_index('ix_pca_tenant_project_control', table_name='project_control_applications')
    op.drop_index('ix_project_control_applications_removed_at', table_name='project_control_applications')
    op.drop_index('ix_project_control_applications_added_by_membership_id', table_name='project_control_applications')
    op.drop_index('ix_project_control_applications_application_id', table_name='project_control_applications')
    op.drop_index('ix_project_control_applications_project_control_id', table_name='project_control_applications')
    op.drop_index('ix_project_control_applications_tenant_id', table_name='project_control_applications')
    op.drop_index('ix_project_control_applications_id', table_name='project_control_applications')
    
    # Drop table
    op.drop_table('project_control_applications')

