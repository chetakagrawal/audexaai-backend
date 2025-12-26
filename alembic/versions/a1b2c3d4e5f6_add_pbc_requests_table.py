"""add_pbc_requests_table

Revision ID: p1q2r3s4t5u6
Revises: 35543335bb6e
Create Date: 2025-01-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'p1q2r3s4t5u6'
down_revision: Union[str, Sequence[str], None] = '35543335bb6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pbc_requests table."""
    
    # Create pbc_requests table
    op.create_table('pbc_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('control_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('owner_membership_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('samples_requested', sa.Integer(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_membership_id'], ['user_tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='PBC requests track evidence requests for control testing'
    )
    
    # Create indexes
    op.create_index('ix_pbc_requests_id', 'pbc_requests', ['id'], unique=False)
    op.create_index('ix_pbc_requests_tenant_id', 'pbc_requests', ['tenant_id'], unique=False)
    op.create_index('ix_pbc_requests_project_id', 'pbc_requests', ['project_id'], unique=False)
    op.create_index('ix_pbc_requests_application_id', 'pbc_requests', ['application_id'], unique=False)
    op.create_index('ix_pbc_requests_control_id', 'pbc_requests', ['control_id'], unique=False)
    op.create_index('ix_pbc_requests_owner_membership_id', 'pbc_requests', ['owner_membership_id'], unique=False)
    
    # Composite indexes for common query patterns
    op.create_index('ix_pbc_requests_tenant_id_id', 'pbc_requests', ['tenant_id', 'id'], unique=False)
    op.create_index('ix_pbc_requests_tenant_id_project_id', 'pbc_requests', ['tenant_id', 'project_id'], unique=False)
    op.create_index('ix_pbc_requests_tenant_id_status', 'pbc_requests', ['tenant_id', 'status'], unique=False)


def downgrade() -> None:
    """Remove pbc_requests table."""
    op.drop_index('ix_pbc_requests_tenant_id_status', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_tenant_id_project_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_tenant_id_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_owner_membership_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_control_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_application_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_project_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_tenant_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_id', table_name='pbc_requests')
    op.drop_table('pbc_requests')
