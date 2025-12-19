"""add_audit_metadata_and_row_version_to_applications

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add audit metadata and row_version to applications table."""
    
    # Add created_by_membership_id column (nullable for legacy rows)
    op.add_column('applications',
        sa.Column('created_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_applications_created_by_membership_id',
        'applications', 'user_tenants',
        ['created_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_applications_created_by_membership_id', 'applications', ['created_by_membership_id'], unique=False)
    
    # Add updated_at column (NOT NULL with default)
    # For existing rows, set updated_at to created_at
    op.add_column('applications',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )
    # Set updated_at to created_at for existing rows
    op.execute("UPDATE applications SET updated_at = created_at WHERE updated_at IS NULL")
    # Now make it NOT NULL
    op.alter_column('applications', 'updated_at', nullable=False, server_default=sa.func.now())
    
    # Add updated_by_membership_id column
    op.add_column('applications',
        sa.Column('updated_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_applications_updated_by_membership_id',
        'applications', 'user_tenants',
        ['updated_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_applications_updated_by_membership_id', 'applications', ['updated_by_membership_id'], unique=False)
    
    # Add deleted_at column
    op.add_column('applications',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_applications_deleted_at', 'applications', ['deleted_at'], unique=False)
    
    # Add deleted_by_membership_id column
    op.add_column('applications',
        sa.Column('deleted_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_applications_deleted_by_membership_id',
        'applications', 'user_tenants',
        ['deleted_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_applications_deleted_by_membership_id', 'applications', ['deleted_by_membership_id'], unique=False)
    
    # Add row_version column (NOT NULL with default)
    op.add_column('applications',
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='1')
    )
    
    # Backfill existing rows: set row_version=1 explicitly (though default should handle it)
    op.execute("""
        UPDATE applications 
        SET row_version = 1 
        WHERE row_version IS NULL
    """)
    
    # Check if there's an existing unique constraint on (tenant_id, name)
    # If it exists, drop it first
    # Use raw SQL to check and drop conditionally
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'uq_applications_tenant_id_name' 
                AND conrelid = 'applications'::regclass
            ) THEN
                ALTER TABLE applications DROP CONSTRAINT uq_applications_tenant_id_name;
            END IF;
        END $$;
    """)
    
    # Create partial unique index: (tenant_id, name) WHERE deleted_at IS NULL
    # This enforces uniqueness only for active (non-deleted) applications
    op.execute("""
        CREATE UNIQUE INDEX ux_applications_tenant_name_active 
        ON applications (tenant_id, name) 
        WHERE deleted_at IS NULL
    """)


def downgrade() -> None:
    """Downgrade schema - remove audit metadata and row_version from applications."""
    
    # Drop partial unique index
    op.execute("DROP INDEX IF EXISTS ux_applications_tenant_name_active")
    
    # Recreate the old unique constraint (if it existed)
    # Note: We don't know the original constraint name, so we'll create a generic one
    try:
        op.create_unique_constraint('uq_applications_tenant_id_name', 'applications', ['tenant_id', 'name'])
    except Exception:
        # Constraint might already exist, continue
        pass
    
    # Remove indexes
    op.drop_index('ix_applications_deleted_by_membership_id', table_name='applications')
    op.drop_index('ix_applications_deleted_at', table_name='applications')
    op.drop_index('ix_applications_updated_by_membership_id', table_name='applications')
    op.drop_index('ix_applications_created_by_membership_id', table_name='applications')
    
    # Remove foreign keys
    op.drop_constraint('fk_applications_deleted_by_membership_id', 'applications', type_='foreignkey')
    op.drop_constraint('fk_applications_updated_by_membership_id', 'applications', type_='foreignkey')
    op.drop_constraint('fk_applications_created_by_membership_id', 'applications', type_='foreignkey')
    
    # Remove columns
    op.drop_column('applications', 'row_version')
    op.drop_column('applications', 'deleted_by_membership_id')
    op.drop_column('applications', 'deleted_at')
    op.drop_column('applications', 'updated_by_membership_id')
    op.drop_column('applications', 'updated_at')
    op.drop_column('applications', 'created_by_membership_id')

