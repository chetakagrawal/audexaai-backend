"""add_version_freezing_to_project_controls

Revision ID: 5488bccb5e13
Revises: 8222adc9acb4
Create Date: 2025-12-19 22:51:59.486850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5488bccb5e13'
down_revision: Union[str, Sequence[str], None] = '8222adc9acb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add version freezing columns and fix uniqueness constraint for project_controls."""
    
    # 1. Add control_version_num column (NOT NULL)
    # Set default to 1 for existing rows, then remove default for new rows
    op.add_column('project_controls', 
        sa.Column('control_version_num', sa.Integer(), nullable=False, server_default='1')
    )
    # Remove server default after backfilling
    op.alter_column('project_controls', 'control_version_num', server_default=None)
    
    # 2. Add added_at column (NOT NULL, default to created_at for existing rows)
    op.execute("""
        ALTER TABLE project_controls 
        ADD COLUMN added_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    """)
    # Copy created_at to added_at for existing rows
    op.execute("UPDATE project_controls SET added_at = created_at WHERE added_at = CURRENT_TIMESTAMP")
    # Remove default after backfilling
    op.alter_column('project_controls', 'added_at', server_default=None)
    
    # 3. Add added_by_membership_id column (NOT NULL for new rows, but existing rows need a value)
    # For existing rows, we'll use updated_by_membership_id if available, otherwise we'll need to handle this
    op.add_column('project_controls',
        sa.Column('added_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    # Backfill from updated_by_membership_id for existing rows
    op.execute("""
        UPDATE project_controls 
        SET added_by_membership_id = updated_by_membership_id 
        WHERE added_by_membership_id IS NULL AND updated_by_membership_id IS NOT NULL
    """)
    # Make it NOT NULL
    op.alter_column('project_controls', 'added_by_membership_id', nullable=False)
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_project_controls_added_by_membership_id',
        'project_controls', 'user_tenants',
        ['added_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    # Add index
    op.create_index(
        'ix_project_controls_added_by_membership_id',
        'project_controls',
        ['added_by_membership_id']
    )
    
    # 4. Add removed_at column (nullable - for soft delete)
    op.add_column('project_controls',
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True)
    )
    # Copy deleted_at to removed_at for existing soft-deleted rows
    op.execute("""
        UPDATE project_controls 
        SET removed_at = deleted_at 
        WHERE deleted_at IS NOT NULL
    """)
    # Add index
    op.create_index('ix_project_controls_removed_at', 'project_controls', ['removed_at'])
    
    # 5. Add removed_by_membership_id column (nullable)
    op.add_column('project_controls',
        sa.Column('removed_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    # Copy deleted_by_membership_id to removed_by_membership_id for existing soft-deleted rows
    op.execute("""
        UPDATE project_controls 
        SET removed_by_membership_id = deleted_by_membership_id 
        WHERE deleted_by_membership_id IS NOT NULL
    """)
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_project_controls_removed_by_membership_id',
        'project_controls', 'user_tenants',
        ['removed_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    # Add index
    op.create_index(
        'ix_project_controls_removed_by_membership_id',
        'project_controls',
        ['removed_by_membership_id']
    )
    
    # 6. Drop old unique constraint and replace with partial unique index
    # Old constraint: uq_project_control_tenant on (tenant_id, project_id, control_id)
    # New constraint: partial unique index WHERE removed_at IS NULL
    op.drop_constraint('uq_project_control_tenant', 'project_controls', type_='unique')
    
    # Create partial unique index for active records only
    op.execute("""
        CREATE UNIQUE INDEX ux_project_controls_active 
        ON project_controls (tenant_id, project_id, control_id) 
        WHERE removed_at IS NULL
    """)
    
    # 7. Add supporting composite indexes for performance
    op.create_index(
        'ix_project_controls_tenant_project',
        'project_controls',
        ['tenant_id', 'project_id']
    )
    op.create_index(
        'ix_project_controls_tenant_control',
        'project_controls',
        ['tenant_id', 'control_id']
    )


def downgrade() -> None:
    """Remove version freezing columns and restore old uniqueness constraint."""
    
    # Drop supporting indexes
    op.drop_index('ix_project_controls_tenant_control', table_name='project_controls')
    op.drop_index('ix_project_controls_tenant_project', table_name='project_controls')
    
    # Drop partial unique index and restore old constraint
    op.execute('DROP INDEX IF EXISTS ux_project_controls_active')
    op.create_unique_constraint(
        'uq_project_control_tenant',
        'project_controls',
        ['tenant_id', 'project_id', 'control_id']
    )
    
    # Drop new columns (in reverse order)
    op.drop_index('ix_project_controls_removed_by_membership_id', table_name='project_controls')
    op.drop_constraint('fk_project_controls_removed_by_membership_id', 'project_controls', type_='foreignkey')
    op.drop_column('project_controls', 'removed_by_membership_id')
    
    op.drop_index('ix_project_controls_removed_at', table_name='project_controls')
    op.drop_column('project_controls', 'removed_at')
    
    op.drop_index('ix_project_controls_added_by_membership_id', table_name='project_controls')
    op.drop_constraint('fk_project_controls_added_by_membership_id', 'project_controls', type_='foreignkey')
    op.drop_column('project_controls', 'added_by_membership_id')
    
    op.drop_column('project_controls', 'added_at')
    op.drop_column('project_controls', 'control_version_num')
