"""add_evidence_upload_tables

Revision ID: a1b2c3d4e5f6
Revises: m1n2o3p4q5r6
Create Date: 2025-01-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'm1n2o3p4q5r6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create evidence_artifacts, evidence_files_v2, and pbc_request_evidence_files tables."""
    
    # Create evidence_artifacts table
    op.create_table(
        'evidence_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='manual'),
        sa.Column('notes', sa.Text(), nullable=True),
        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by_membership_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['updated_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['deleted_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        comment='Evidence artifacts - containers for evidence uploads'
    )
    
    # Create indexes for evidence_artifacts
    op.create_index('ix_evidence_artifacts_id', 'evidence_artifacts', ['id'], unique=False)
    op.create_index('ix_evidence_artifacts_tenant_id', 'evidence_artifacts', ['tenant_id'], unique=False)
    op.create_index('ix_evidence_artifacts_project_id', 'evidence_artifacts', ['project_id'], unique=False)
    op.create_index('ix_evidence_artifacts_created_by_membership_id', 'evidence_artifacts', ['created_by_membership_id'], unique=False)
    op.create_index('ix_evidence_artifacts_updated_by_membership_id', 'evidence_artifacts', ['updated_by_membership_id'], unique=False)
    op.create_index('ix_evidence_artifacts_deleted_by_membership_id', 'evidence_artifacts', ['deleted_by_membership_id'], unique=False)
    op.create_index('ix_evidence_artifacts_deleted_at', 'evidence_artifacts', ['deleted_at'], unique=False)
    op.create_index('ix_evidence_artifacts_tenant_project', 'evidence_artifacts', ['tenant_id', 'project_id'], unique=False)
    op.create_index('ix_evidence_artifacts_tenant_created_at', 'evidence_artifacts', ['tenant_id', 'created_at'], unique=False)
    
    # Create evidence_files_v2 table
    op.create_table(
        'evidence_files_v2',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('artifact_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('storage_key', sa.Text(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by_membership_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['artifact_id'], ['evidence_artifacts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['updated_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['deleted_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        comment='Evidence files v2 - files within evidence artifacts'
    )
    
    # Create indexes for evidence_files_v2
    op.create_index('ix_evidence_files_v2_id', 'evidence_files_v2', ['id'], unique=False)
    op.create_index('ix_evidence_files_v2_tenant_id', 'evidence_files_v2', ['tenant_id'], unique=False)
    op.create_index('ix_evidence_files_v2_project_id', 'evidence_files_v2', ['project_id'], unique=False)
    op.create_index('ix_evidence_files_v2_artifact_id', 'evidence_files_v2', ['artifact_id'], unique=False)
    op.create_index('ix_evidence_files_v2_created_by_membership_id', 'evidence_files_v2', ['created_by_membership_id'], unique=False)
    op.create_index('ix_evidence_files_v2_updated_by_membership_id', 'evidence_files_v2', ['updated_by_membership_id'], unique=False)
    op.create_index('ix_evidence_files_v2_deleted_by_membership_id', 'evidence_files_v2', ['deleted_by_membership_id'], unique=False)
    op.create_index('ix_evidence_files_v2_deleted_at', 'evidence_files_v2', ['deleted_at'], unique=False)
    op.create_index('ix_evidence_files_v2_tenant_project', 'evidence_files_v2', ['tenant_id', 'project_id'], unique=False)
    op.create_index('ix_evidence_files_v2_tenant_artifact', 'evidence_files_v2', ['tenant_id', 'artifact_id'], unique=False)
    op.create_index('ix_evidence_files_v2_tenant_sha256', 'evidence_files_v2', ['tenant_id', 'sha256'], unique=False)
    
    # Create pbc_request_evidence_files link table
    op.create_table(
        'pbc_request_evidence_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pbc_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('evidence_file_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Audit fields
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_by_membership_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('row_version', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pbc_request_id'], ['pbc_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_file_id'], ['evidence_files_v2.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['deleted_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        comment='Links between PBC requests and evidence files'
    )
    
    # Create indexes for pbc_request_evidence_files
    op.create_index('ix_pbc_request_evidence_files_id', 'pbc_request_evidence_files', ['id'], unique=False)
    op.create_index('ix_pbc_request_evidence_files_tenant_id', 'pbc_request_evidence_files', ['tenant_id'], unique=False)
    op.create_index('ix_pbc_request_evidence_files_project_id', 'pbc_request_evidence_files', ['project_id'], unique=False)
    op.create_index('ix_pbc_request_evidence_files_pbc_request_id', 'pbc_request_evidence_files', ['pbc_request_id'], unique=False)
    op.create_index('ix_pbc_request_evidence_files_evidence_file_id', 'pbc_request_evidence_files', ['evidence_file_id'], unique=False)
    op.create_index('ix_pbc_request_evidence_files_created_by_membership_id', 'pbc_request_evidence_files', ['created_by_membership_id'], unique=False)
    op.create_index('ix_pbc_request_evidence_files_deleted_by_membership_id', 'pbc_request_evidence_files', ['deleted_by_membership_id'], unique=False)
    op.create_index('ix_pbc_request_evidence_files_deleted_at', 'pbc_request_evidence_files', ['deleted_at'], unique=False)
    
    # Create unique partial index for active links
    op.execute(sa.text("""
        CREATE UNIQUE INDEX ux_pbc_request_evidence_files_active
        ON pbc_request_evidence_files (tenant_id, pbc_request_id, evidence_file_id)
        WHERE deleted_at IS NULL
    """))


def downgrade() -> None:
    """Drop evidence_artifacts, evidence_files_v2, and pbc_request_evidence_files tables."""
    
    # Drop unique partial index
    op.drop_index('ux_pbc_request_evidence_files_active', table_name='pbc_request_evidence_files')
    
    # Drop indexes for pbc_request_evidence_files
    op.drop_index('ix_pbc_request_evidence_files_deleted_at', table_name='pbc_request_evidence_files')
    op.drop_index('ix_pbc_request_evidence_files_deleted_by_membership_id', table_name='pbc_request_evidence_files')
    op.drop_index('ix_pbc_request_evidence_files_created_by_membership_id', table_name='pbc_request_evidence_files')
    op.drop_index('ix_pbc_request_evidence_files_evidence_file_id', table_name='pbc_request_evidence_files')
    op.drop_index('ix_pbc_request_evidence_files_pbc_request_id', table_name='pbc_request_evidence_files')
    op.drop_index('ix_pbc_request_evidence_files_project_id', table_name='pbc_request_evidence_files')
    op.drop_index('ix_pbc_request_evidence_files_tenant_id', table_name='pbc_request_evidence_files')
    op.drop_index('ix_pbc_request_evidence_files_id', table_name='pbc_request_evidence_files')
    
    # Drop pbc_request_evidence_files table
    op.drop_table('pbc_request_evidence_files')
    
    # Drop indexes for evidence_files_v2
    op.drop_index('ix_evidence_files_v2_tenant_sha256', table_name='evidence_files_v2')
    op.drop_index('ix_evidence_files_v2_tenant_artifact', table_name='evidence_files_v2')
    op.drop_index('ix_evidence_files_v2_tenant_project', table_name='evidence_files_v2')
    op.drop_index('ix_evidence_files_v2_deleted_at', table_name='evidence_files_v2')
    op.drop_index('ix_evidence_files_v2_deleted_by_membership_id', table_name='evidence_files_v2')
    op.drop_index('ix_evidence_files_v2_updated_by_membership_id', table_name='evidence_files_v2')
    op.drop_index('ix_evidence_files_v2_created_by_membership_id', table_name='evidence_files_v2')
    op.drop_index('ix_evidence_files_v2_artifact_id', table_name='evidence_files_v2')
    op.drop_index('ix_evidence_files_v2_project_id', table_name='evidence_files_v2')
    op.drop_index('ix_evidence_files_v2_tenant_id', table_name='evidence_files_v2')
    op.drop_index('ix_evidence_files_v2_id', table_name='evidence_files_v2')
    
    # Drop evidence_files_v2 table
    op.drop_table('evidence_files_v2')
    
    # Drop indexes for evidence_artifacts
    op.drop_index('ix_evidence_artifacts_tenant_created_at', table_name='evidence_artifacts')
    op.drop_index('ix_evidence_artifacts_tenant_project', table_name='evidence_artifacts')
    op.drop_index('ix_evidence_artifacts_deleted_at', table_name='evidence_artifacts')
    op.drop_index('ix_evidence_artifacts_deleted_by_membership_id', table_name='evidence_artifacts')
    op.drop_index('ix_evidence_artifacts_updated_by_membership_id', table_name='evidence_artifacts')
    op.drop_index('ix_evidence_artifacts_created_by_membership_id', table_name='evidence_artifacts')
    op.drop_index('ix_evidence_artifacts_project_id', table_name='evidence_artifacts')
    op.drop_index('ix_evidence_artifacts_tenant_id', table_name='evidence_artifacts')
    op.drop_index('ix_evidence_artifacts_id', table_name='evidence_artifacts')
    
    # Drop evidence_artifacts table
    op.drop_table('evidence_artifacts')

