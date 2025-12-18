"""add_soft_delete_and_modification_tracking_to_project_controls

Revision ID: 8c09d731b5d9
Revises: c3d4e5f6a7b8
Create Date: 2025-12-17 22:46:12.288425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8c09d731b5d9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add soft delete and modification tracking to project_controls."""
    # Add updated_at column
    op.add_column('project_controls',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add updated_by_membership_id column
    op.add_column('project_controls',
        sa.Column('updated_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_project_controls_updated_by_membership_id',
        'project_controls', 'user_tenants',
        ['updated_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_project_controls_updated_by_membership_id', 'project_controls', ['updated_by_membership_id'], unique=False)
    
    # Add deleted_at column
    op.add_column('project_controls',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_project_controls_deleted_at', 'project_controls', ['deleted_at'], unique=False)
    
    # Add deleted_by_membership_id column
    op.add_column('project_controls',
        sa.Column('deleted_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_project_controls_deleted_by_membership_id',
        'project_controls', 'user_tenants',
        ['deleted_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_project_controls_deleted_by_membership_id', 'project_controls', ['deleted_by_membership_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - remove soft delete and modification tracking from project_controls."""
    # Remove indexes
    op.drop_index('ix_project_controls_deleted_by_membership_id', table_name='project_controls')
    op.drop_index('ix_project_controls_deleted_at', table_name='project_controls')
    op.drop_index('ix_project_controls_updated_by_membership_id', table_name='project_controls')
    
    # Remove foreign keys
    op.drop_constraint('fk_project_controls_deleted_by_membership_id', 'project_controls', type_='foreignkey')
    op.drop_constraint('fk_project_controls_updated_by_membership_id', 'project_controls', type_='foreignkey')
    
    # Remove columns
    op.drop_column('project_controls', 'deleted_by_membership_id')
    op.drop_column('project_controls', 'deleted_at')
    op.drop_column('project_controls', 'updated_by_membership_id')
    op.drop_column('project_controls', 'updated_at')
