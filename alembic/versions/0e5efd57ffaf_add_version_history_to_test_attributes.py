"""add_version_history_to_test_attributes

Revision ID: 0e5efd57ffaf
Revises: 4271a2cf3387
Create Date: 2025-12-19 16:39:40.014338

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0e5efd57ffaf'
down_revision: Union[str, Sequence[str], None] = '4271a2cf3387'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add version history support to test_attributes table."""
    # Add audit metadata columns
    op.add_column('test_attributes', sa.Column('created_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('test_attributes', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('test_attributes', sa.Column('updated_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('test_attributes', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('test_attributes', sa.Column('deleted_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('test_attributes', sa.Column('row_version', sa.Integer(), nullable=True))
    
    # Backfill safely
    op.execute("""
        UPDATE test_attributes
        SET row_version = 1
        WHERE row_version IS NULL;
    """)
    op.execute("""
        UPDATE test_attributes
        SET updated_at = created_at
        WHERE updated_at IS NULL;
    """)
    
    # Make columns NOT NULL after backfill
    op.alter_column('test_attributes', 'row_version', nullable=False, server_default='1')
    op.alter_column('test_attributes', 'updated_at', nullable=False)
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_test_attributes_created_by_membership',
        'test_attributes', 'user_tenants',
        ['created_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'fk_test_attributes_updated_by_membership',
        'test_attributes', 'user_tenants',
        ['updated_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'fk_test_attributes_deleted_by_membership',
        'test_attributes', 'user_tenants',
        ['deleted_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    
    # Create indexes
    op.create_index('ix_test_attributes_created_by_membership_id', 'test_attributes', ['created_by_membership_id'], unique=False)
    op.create_index('ix_test_attributes_updated_by_membership_id', 'test_attributes', ['updated_by_membership_id'], unique=False)
    op.create_index('ix_test_attributes_deleted_at', 'test_attributes', ['deleted_at'], unique=False)
    op.create_index('ix_test_attributes_deleted_by_membership_id', 'test_attributes', ['deleted_by_membership_id'], unique=False)
    
    # Add partial unique index: (tenant_id, control_id, code) must be unique for ACTIVE test attributes
    op.execute("""
        CREATE UNIQUE INDEX ux_test_attributes_active_code
        ON test_attributes (tenant_id, control_id, code)
        WHERE deleted_at IS NULL;
    """)
    
    # Create trigger for version history (uses existing generic function)
    op.execute("""
        CREATE TRIGGER trigger_audit_capture_test_attribute_version
        BEFORE UPDATE OR DELETE ON test_attributes
        FOR EACH ROW
        EXECUTE FUNCTION audit_capture_entity_version();
    """)


def downgrade() -> None:
    """Remove version history support from test_attributes table."""
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS trigger_audit_capture_test_attribute_version ON test_attributes;")
    
    # Drop partial unique index
    op.drop_index('ux_test_attributes_active_code', table_name='test_attributes')
    
    # Drop indexes
    op.drop_index('ix_test_attributes_deleted_by_membership_id', table_name='test_attributes')
    op.drop_index('ix_test_attributes_deleted_at', table_name='test_attributes')
    op.drop_index('ix_test_attributes_updated_by_membership_id', table_name='test_attributes')
    op.drop_index('ix_test_attributes_created_by_membership_id', table_name='test_attributes')
    
    # Drop foreign key constraints
    op.drop_constraint('fk_test_attributes_deleted_by_membership', 'test_attributes', type_='foreignkey')
    op.drop_constraint('fk_test_attributes_updated_by_membership', 'test_attributes', type_='foreignkey')
    op.drop_constraint('fk_test_attributes_created_by_membership', 'test_attributes', type_='foreignkey')
    
    # Drop columns
    op.drop_column('test_attributes', 'row_version')
    op.drop_column('test_attributes', 'deleted_by_membership_id')
    op.drop_column('test_attributes', 'deleted_at')
    op.drop_column('test_attributes', 'updated_by_membership_id')
    op.drop_column('test_attributes', 'updated_at')
    op.drop_column('test_attributes', 'created_by_membership_id')
