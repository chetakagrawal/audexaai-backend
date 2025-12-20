"""add_audit_metadata_to_projects

Revision ID: 1c8c9518a387
Revises: 08086e84d319
Create Date: 2025-12-19 21:47:44.265671

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '1c8c9518a387'
down_revision: Union[str, Sequence[str], None] = '08086e84d319'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add audit metadata and row_version to projects table.
    
    Projects already have created_by_membership_id, so we only add:
    - updated_at (nullable DateTime, matches controls/applications pattern)
    - updated_by_membership_id (nullable UUID FK to user_tenants)
    - row_version (NOT NULL Integer, default=1)
    - deleted_at and deleted_by_membership_id for soft delete support (for consistency with other entities)
    """
    
    # Add updated_at column (nullable, following the pattern from a95a6bf8fc4b)
    # NULL = never updated, Non-NULL = last update timestamp
    op.add_column('projects',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_projects_updated_at', 'projects', ['updated_at'], unique=False)
    
    # Add updated_by_membership_id column
    op.add_column('projects',
        sa.Column('updated_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_projects_updated_by_membership_id',
        'projects', 'user_tenants',
        ['updated_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_projects_updated_by_membership_id', 'projects', ['updated_by_membership_id'], unique=False)
    
    # Add deleted_at column (for soft delete support, following controls/applications pattern)
    op.add_column('projects',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_projects_deleted_at', 'projects', ['deleted_at'], unique=False)
    
    # Add deleted_by_membership_id column
    op.add_column('projects',
        sa.Column('deleted_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_projects_deleted_by_membership_id',
        'projects', 'user_tenants',
        ['deleted_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_projects_deleted_by_membership_id', 'projects', ['deleted_by_membership_id'], unique=False)
    
    # Add row_version column (NOT NULL with default)
    op.add_column('projects',
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='1')
    )
    
    # Backfill existing rows: set row_version=1 explicitly (though default should handle it)
    op.execute("""
        UPDATE projects 
        SET row_version = 1 
        WHERE row_version IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema - remove audit metadata and row_version from projects."""
    
    # Remove indexes
    op.drop_index('ix_projects_deleted_by_membership_id', table_name='projects')
    op.drop_index('ix_projects_deleted_at', table_name='projects')
    op.drop_index('ix_projects_updated_by_membership_id', table_name='projects')
    op.drop_index('ix_projects_updated_at', table_name='projects')
    
    # Remove foreign keys
    op.drop_constraint('fk_projects_deleted_by_membership_id', 'projects', type_='foreignkey')
    op.drop_constraint('fk_projects_updated_by_membership_id', 'projects', type_='foreignkey')
    
    # Remove columns
    op.drop_column('projects', 'row_version')
    op.drop_column('projects', 'deleted_by_membership_id')
    op.drop_column('projects', 'deleted_at')
    op.drop_column('projects', 'updated_by_membership_id')
    op.drop_column('projects', 'updated_at')
