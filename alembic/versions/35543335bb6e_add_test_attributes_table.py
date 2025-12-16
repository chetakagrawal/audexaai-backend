"""add_test_attributes_table

Revision ID: 35543335bb6e
Revises: 2cceb1192c50
Create Date: 2025-12-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '35543335bb6e'
down_revision: Union[str, Sequence[str], None] = '2cceb1192c50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add test_attributes table."""
    
    # Create test_attributes table (tenant-owned, linked to controls)
    op.create_table('test_attributes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('control_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('frequency', sa.String(length=50), nullable=True),
        sa.Column('test_procedure', sa.Text(), nullable=True),
        sa.Column('expected_evidence', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['control_id'], ['controls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        comment='Test attributes define test procedures and expected evidence for controls'
    )
    
    # Create indexes
    op.create_index('ix_test_attributes_id', 'test_attributes', ['id'], unique=False)
    op.create_index('ix_test_attributes_tenant_id', 'test_attributes', ['tenant_id'], unique=False)
    op.create_index('ix_test_attributes_control_id', 'test_attributes', ['control_id'], unique=False)
    # Composite index for tenant-scoped lookups
    op.create_index('ix_test_attributes_tenant_id_id', 'test_attributes', ['tenant_id', 'id'], unique=False)
    # Composite index for control lookups within tenant
    op.create_index('ix_test_attributes_tenant_id_control_id', 'test_attributes', ['tenant_id', 'control_id'], unique=False)


def downgrade() -> None:
    """Remove test_attributes table."""
    op.drop_index('ix_test_attributes_tenant_id_control_id', table_name='test_attributes')
    op.drop_index('ix_test_attributes_tenant_id_id', table_name='test_attributes')
    op.drop_index('ix_test_attributes_control_id', table_name='test_attributes')
    op.drop_index('ix_test_attributes_tenant_id', table_name='test_attributes')
    op.drop_index('ix_test_attributes_id', table_name='test_attributes')
    op.drop_table('test_attributes')
