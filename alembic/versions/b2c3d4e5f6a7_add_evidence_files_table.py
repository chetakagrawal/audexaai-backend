"""add_evidence_files_table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-10 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add evidence_files table."""
    
    # Create evidence_files table
    op.create_table('evidence_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pbc_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sample_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uploaded_by_membership_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('storage_uri', sa.String(length=512), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('supersedes_file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pbc_request_id'], ['pbc_requests.id'], ondelete='CASCADE'),
        # Note: sample_id FK will be added when samples table is implemented
        sa.ForeignKeyConstraint(['uploaded_by_membership_id'], ['user_tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supersedes_file_id'], ['evidence_files.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        comment='Evidence files uploaded for PBC requests and samples'
    )
    
    # Create indexes
    op.create_index('ix_evidence_files_id', 'evidence_files', ['id'], unique=False)
    op.create_index('ix_evidence_files_tenant_id', 'evidence_files', ['tenant_id'], unique=False)
    op.create_index('ix_evidence_files_pbc_request_id', 'evidence_files', ['pbc_request_id'], unique=False)
    op.create_index('ix_evidence_files_sample_id', 'evidence_files', ['sample_id'], unique=False)
    op.create_index('ix_evidence_files_uploaded_by_membership_id', 'evidence_files', ['uploaded_by_membership_id'], unique=False)
    
    # Composite indexes for common query patterns
    op.create_index('ix_evidence_files_tenant_id_id', 'evidence_files', ['tenant_id', 'id'], unique=False)
    op.create_index('ix_evidence_files_tenant_id_pbc_request_id', 'evidence_files', ['tenant_id', 'pbc_request_id'], unique=False)
    op.create_index('ix_evidence_files_tenant_id_uploaded_at', 'evidence_files', ['tenant_id', 'uploaded_at'], unique=False)


def downgrade() -> None:
    """Remove evidence_files table."""
    op.drop_index('ix_evidence_files_tenant_id_uploaded_at', table_name='evidence_files')
    op.drop_index('ix_evidence_files_tenant_id_pbc_request_id', table_name='evidence_files')
    op.drop_index('ix_evidence_files_tenant_id_id', table_name='evidence_files')
    op.drop_index('ix_evidence_files_uploaded_by_membership_id', table_name='evidence_files')
    op.drop_index('ix_evidence_files_sample_id', table_name='evidence_files')
    op.drop_index('ix_evidence_files_pbc_request_id', table_name='evidence_files')
    op.drop_index('ix_evidence_files_tenant_id', table_name='evidence_files')
    op.drop_index('ix_evidence_files_id', table_name='evidence_files')
    op.drop_table('evidence_files')
