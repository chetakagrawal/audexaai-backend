"""add_audit_metadata_and_row_version_to_controls

Revision ID: f1a2b3c4d5e6
Revises: 8c09d731b5d9
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = '8c09d731b5d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add audit metadata and row_version to controls table."""
    
    # Add updated_at column (NOT NULL with default)
    # For existing rows, set updated_at to created_at
    op.add_column('controls',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )
    # Set updated_at to created_at for existing rows
    op.execute("UPDATE controls SET updated_at = created_at WHERE updated_at IS NULL")
    # Now make it NOT NULL
    op.alter_column('controls', 'updated_at', nullable=False, server_default=sa.func.now())
    
    # Add updated_by_membership_id column
    op.add_column('controls',
        sa.Column('updated_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_controls_updated_by_membership_id',
        'controls', 'user_tenants',
        ['updated_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_controls_updated_by_membership_id', 'controls', ['updated_by_membership_id'], unique=False)
    
    # Add deleted_at column
    op.add_column('controls',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_controls_deleted_at', 'controls', ['deleted_at'], unique=False)
    
    # Add deleted_by_membership_id column
    op.add_column('controls',
        sa.Column('deleted_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_controls_deleted_by_membership_id',
        'controls', 'user_tenants',
        ['deleted_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_controls_deleted_by_membership_id', 'controls', ['deleted_by_membership_id'], unique=False)
    
    # Add row_version column (NOT NULL with default)
    op.add_column('controls',
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='1')
    )
    
    # Backfill existing rows: set updated_at to created_at if it's null (shouldn't happen but be safe)
    # Note: updated_at already has server_default=now(), so existing rows will have it set
    # But we'll also set row_version=1 explicitly for existing rows (though default should handle it)
    op.execute("""
        UPDATE controls 
        SET row_version = 1 
        WHERE row_version IS NULL
    """)
    
    # Drop the old unique constraint on (tenant_id, control_code)
    # The original constraint is named 'uq_controls_tenant_id_control_code'
    op.drop_constraint('uq_controls_tenant_id_control_code', 'controls', type_='unique')
    
    # Create partial unique index: (tenant_id, control_code) WHERE deleted_at IS NULL
    # This enforces uniqueness only for active (non-deleted) controls
    op.execute("""
        CREATE UNIQUE INDEX ux_controls_tenant_code_active 
        ON controls (tenant_id, control_code) 
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema - remove audit metadata and row_version from controls."""
    
    # Drop partial unique index
    op.execute("DROP INDEX IF EXISTS ux_controls_tenant_code_active")
    
    # Recreate the old unique constraint
    op.create_unique_constraint('uq_controls_tenant_id_control_code', 'controls', ['tenant_id', 'control_code'])
    
    # Remove indexes
    op.drop_index('ix_controls_deleted_by_membership_id', table_name='controls')
    op.drop_index('ix_controls_deleted_at', table_name='controls')
    op.drop_index('ix_controls_updated_by_membership_id', table_name='controls')
    
    # Remove foreign keys
    op.drop_constraint('fk_controls_deleted_by_membership_id', 'controls', type_='foreignkey')
    op.drop_constraint('fk_controls_updated_by_membership_id', 'controls', type_='foreignkey')
    
    # Remove columns
    op.drop_column('controls', 'row_version')
    op.drop_column('controls', 'deleted_by_membership_id')
    op.drop_column('controls', 'deleted_at')
    op.drop_column('controls', 'updated_by_membership_id')
    op.drop_column('controls', 'updated_at')

