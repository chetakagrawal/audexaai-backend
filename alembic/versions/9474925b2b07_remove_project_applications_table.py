"""remove_project_applications_table

Revision ID: 9474925b2b07
Revises: d46d61482b1f
Create Date: 2025-12-20 13:20:26.255559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9474925b2b07'
down_revision: Union[str, Sequence[str], None] = 'd46d61482b1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove project_applications table and all associated indexes."""
    # Drop indexes first (using raw SQL with IF EXISTS)
    op.execute("DROP INDEX IF EXISTS ix_project_applications_tenant_id_id;")
    op.execute("DROP INDEX IF EXISTS ix_project_applications_id;")
    op.execute("DROP INDEX IF EXISTS ix_project_applications_application_id;")
    op.execute("DROP INDEX IF EXISTS ix_project_applications_project_id;")
    op.execute("DROP INDEX IF EXISTS ix_project_applications_tenant_id;")
    
    # Drop the table (this will also drop the unique constraint and foreign keys)
    op.execute("DROP TABLE IF EXISTS project_applications CASCADE;")


def downgrade() -> None:
    """Recreate project_applications table (for rollback purposes)."""
    from sqlalchemy.dialects import postgresql
    
    # Recreate the table
    op.create_table('project_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'project_id', 'application_id', name='uq_project_application_tenant'),
        comment='Join table linking projects to applications with tenant isolation'
    )
    
    # Recreate indexes
    op.create_index('ix_project_applications_tenant_id', 'project_applications', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_project_applications_project_id'), 'project_applications', ['project_id'], unique=False)
    op.create_index(op.f('ix_project_applications_application_id'), 'project_applications', ['application_id'], unique=False)
    op.create_index(op.f('ix_project_applications_id'), 'project_applications', ['id'], unique=False)
    op.create_index('ix_project_applications_tenant_id_id', 'project_applications', ['tenant_id', 'id'], unique=False)
