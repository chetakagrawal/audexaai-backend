"""add_entity_versions_table

Revision ID: d7887576e4a5
Revises: a95a6bf8fc4b
Create Date: 2025-12-19 14:54:02.544804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd7887576e4a5'
down_revision: Union[str, Sequence[str], None] = 'a95a6bf8fc4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create entity_versions table for generic version history."""
    op.create_table(
        'entity_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.Text(), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('operation', sa.Text(), nullable=False),
        sa.Column('version_num', sa.Integer(), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('changed_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('data', postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("operation IN ('UPDATE', 'DELETE')", name='ck_entity_versions_operation'),
    )
    
    # Create indexes
    op.create_index(
        'ix_entity_versions_tenant_entity_version',
        'entity_versions',
        ['tenant_id', 'entity_type', 'entity_id', sa.text('version_num DESC')],
    )
    op.create_index(
        'ix_entity_versions_tenant_entity_valid',
        'entity_versions',
        ['tenant_id', 'entity_type', 'entity_id', 'valid_from', 'valid_to'],
    )
    op.create_index(
        'ix_entity_versions_changed_by',
        'entity_versions',
        ['changed_by_membership_id'],
    )


def downgrade() -> None:
    """Drop entity_versions table."""
    op.drop_index('ix_entity_versions_changed_by', table_name='entity_versions')
    op.drop_index('ix_entity_versions_tenant_entity_valid', table_name='entity_versions')
    op.drop_index('ix_entity_versions_tenant_entity_version', table_name='entity_versions')
    op.drop_table('entity_versions')
