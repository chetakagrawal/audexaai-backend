"""add_effective_dating_to_control_applications

Revision ID: g9h0i1j2k3l4
Revises: a7b8c9d0e1f2
Create Date: 2025-01-XX XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'g9h0i1j2k3l4'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add effective dating to control_applications table."""
    
    # Rename created_at to added_at
    op.alter_column('control_applications', 'created_at',
                    new_column_name='added_at',
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)
    
    # Add added_by_membership_id column (nullable for legacy rows)
    op.add_column('control_applications',
        sa.Column('added_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_control_apps_added_by_membership',
        'control_applications',
        'user_tenants',
        ['added_by_membership_id'],
        ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_control_apps_added_by_membership_id', 'control_applications', ['added_by_membership_id'])
    
    # Add removed_at column (nullable)
    op.add_column('control_applications',
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('ix_control_apps_removed_at', 'control_applications', ['removed_at'])
    
    # Add removed_by_membership_id column (nullable)
    op.add_column('control_applications',
        sa.Column('removed_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        'fk_control_apps_removed_by_membership',
        'control_applications',
        'user_tenants',
        ['removed_by_membership_id'],
        ['id'],
        ondelete='RESTRICT'
    )
    op.create_index('ix_control_apps_removed_by_membership_id', 'control_applications', ['removed_by_membership_id'])
    
    # Drop old unique constraint
    op.drop_constraint('uq_control_application_tenant', 'control_applications', type_='unique')
    
    # Create partial unique index for ACTIVE mappings only
    op.create_index(
        'ux_control_apps_active',
        'control_applications',
        ['tenant_id', 'control_id', 'application_id'],
        unique=True,
        postgresql_where=sa.text('removed_at IS NULL')
    )
    
    # Create supporting indexes
    op.create_index('ix_control_apps_tenant_control', 'control_applications', ['tenant_id', 'control_id'])
    op.create_index('ix_control_apps_tenant_application', 'control_applications', ['tenant_id', 'application_id'])


def downgrade() -> None:
    """Downgrade schema - remove effective dating from control_applications table."""
    
    # Drop supporting indexes
    op.drop_index('ix_control_apps_tenant_application', table_name='control_applications')
    op.drop_index('ix_control_apps_tenant_control', table_name='control_applications')
    
    # Drop partial unique index
    op.drop_index('ux_control_apps_active', table_name='control_applications')
    
    # Restore old unique constraint
    op.create_unique_constraint('uq_control_application_tenant', 'control_applications', ['tenant_id', 'control_id', 'application_id'])
    
    # Drop removed_by_membership_id column
    op.drop_index('ix_control_apps_removed_by_membership_id', table_name='control_applications')
    op.drop_constraint('fk_control_apps_removed_by_membership', 'control_applications', type_='foreignkey')
    op.drop_column('control_applications', 'removed_by_membership_id')
    
    # Drop removed_at column
    op.drop_index('ix_control_apps_removed_at', table_name='control_applications')
    op.drop_column('control_applications', 'removed_at')
    
    # Drop added_by_membership_id column
    op.drop_index('ix_control_apps_added_by_membership_id', table_name='control_applications')
    op.drop_constraint('fk_control_apps_added_by_membership', 'control_applications', type_='foreignkey')
    op.drop_column('control_applications', 'added_by_membership_id')
    
    # Rename added_at back to created_at
    op.alter_column('control_applications', 'added_at',
                    new_column_name='created_at',
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)

