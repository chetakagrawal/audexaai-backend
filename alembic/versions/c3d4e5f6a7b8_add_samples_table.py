"""add samples table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-01-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create samples table
    op.create_table('samples',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pbc_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_number', sa.Integer(), nullable=False),
        sa.Column('identifier', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('test_notes', sa.Text(), nullable=True),
        sa.Column('tested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tested_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pbc_request_id'], ['pbc_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tested_by_membership_id'], ['user_tenants.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='Samples for control testing in audit projects'
    )
    
    # Create indexes
    op.create_index(op.f('ix_samples_id'), 'samples', ['id'], unique=False)
    op.create_index(op.f('ix_samples_tenant_id'), 'samples', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_samples_pbc_request_id'), 'samples', ['pbc_request_id'], unique=False)
    op.create_index(op.f('ix_samples_tested_by_membership_id'), 'samples', ['tested_by_membership_id'], unique=False)

    # Add foreign key constraint from evidence_files.sample_id to samples.id
    # This was deferred when creating the evidence_files table
    op.create_foreign_key(
        'fk_evidence_files_sample_id_samples',
        'evidence_files', 'samples',
        ['sample_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove foreign key constraint from evidence_files
    op.drop_constraint('fk_evidence_files_sample_id_samples', 'evidence_files', type_='foreignkey')
    
    # Drop indexes
    op.drop_index(op.f('ix_samples_tested_by_membership_id'), table_name='samples')
    op.drop_index(op.f('ix_samples_pbc_request_id'), table_name='samples')
    op.drop_index(op.f('ix_samples_tenant_id'), table_name='samples')
    op.drop_index(op.f('ix_samples_id'), table_name='samples')
    
    # Drop table
    op.drop_table('samples')
