"""add created_by_membership_id to projects and controls

Revision ID: 5d8a2a7af60d
Revises: cc5f2d94aad1
Create Date: 2025-12-13 21:08:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5d8a2a7af60d'
down_revision: Union[str, Sequence[str], None] = 'cc5f2d94aad1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add created_by_membership_id to projects and controls tables."""
    
    # Check if tables exist (they should from PR2 migration cc5f2d94aad1)
    connection = op.get_bind()
    
    # Verify tables exist
    result = connection.execute(sa.text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('projects', 'controls')
        )
    """))
    tables_exist = result.scalar()
    
    if not tables_exist:
        raise Exception(
            "Tables 'projects' and 'controls' do not exist. "
            "Please run PR2 migration (cc5f2d94aad1) first."
        )
    
    # Check if column already exists (idempotency)
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'projects' 
        AND column_name = 'created_by_membership_id'
    """))
    projects_has_column = result.fetchone() is not None
    
    if not projects_has_column:
        # Step 1: Add nullable created_by_membership_id to projects
        op.add_column('projects', 
            sa.Column('created_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
        )
    
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'controls' 
        AND column_name = 'created_by_membership_id'
    """))
    controls_has_column = result.fetchone() is not None
    
    if not controls_has_column:
        # Step 2: Add nullable created_by_membership_id to controls
        op.add_column('controls',
            sa.Column('created_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True)
        )
    
    # Step 3: Backfill created_by_membership_id for existing rows
    # Since these tables are new (from PR2), they're likely empty
    # But if there are existing rows, we need to handle them
    
    # For projects: If there are existing projects, we can't backfill without creation context
    # We'll set a default membership for each tenant (first admin membership)
    # If no membership exists, migration will fail (which is correct - can't have orphaned projects)
    connection.execute(sa.text("""
        UPDATE projects p
        SET created_by_membership_id = (
            SELECT ut.id
            FROM user_tenants ut
            WHERE ut.tenant_id = p.tenant_id
            ORDER BY ut.created_at ASC
            LIMIT 1
        )
        WHERE p.created_by_membership_id IS NULL
    """))
    
    # For controls: Same approach
    connection.execute(sa.text("""
        UPDATE controls c
        SET created_by_membership_id = (
            SELECT ut.id
            FROM user_tenants ut
            WHERE ut.tenant_id = c.tenant_id
            ORDER BY ut.created_at ASC
            LIMIT 1
        )
        WHERE c.created_by_membership_id IS NULL
    """))
    
    # Step 4: Verify no NULLs remain (migration will fail if any exist)
    # This ensures data integrity before setting NOT NULL
    result = connection.execute(sa.text("""
        SELECT COUNT(*) FROM projects WHERE created_by_membership_id IS NULL
    """))
    projects_null_count = result.scalar()
    
    result = connection.execute(sa.text("""
        SELECT COUNT(*) FROM controls WHERE created_by_membership_id IS NULL
    """))
    controls_null_count = result.scalar()
    
    if projects_null_count > 0:
        raise Exception(f'Cannot set NOT NULL: projects table has {projects_null_count} rows with NULL created_by_membership_id')
    if controls_null_count > 0:
        raise Exception(f'Cannot set NOT NULL: controls table has {controls_null_count} rows with NULL created_by_membership_id')
    
    # Step 5: Set NOT NULL (only if column was just added)
    if not projects_has_column:
        op.alter_column('projects', 'created_by_membership_id', nullable=False)
    if not controls_has_column:
        op.alter_column('controls', 'created_by_membership_id', nullable=False)
    
    # Step 6: Add FK constraints (check if they exist first)
    result = connection.execute(sa.text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'projects' 
        AND constraint_name = 'fk_projects_created_by_membership_id'
    """))
    projects_fk_exists = result.fetchone() is not None
    
    if not projects_fk_exists:
        op.create_foreign_key(
            'fk_projects_created_by_membership_id',
            'projects', 'user_tenants',
            ['created_by_membership_id'], ['id'],
            ondelete='RESTRICT'
        )
    
    result = connection.execute(sa.text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'controls' 
        AND constraint_name = 'fk_controls_created_by_membership_id'
    """))
    controls_fk_exists = result.fetchone() is not None
    
    if not controls_fk_exists:
        op.create_foreign_key(
            'fk_controls_created_by_membership_id',
            'controls', 'user_tenants',
            ['created_by_membership_id'], ['id'],
            ondelete='RESTRICT'
        )
    
    # Step 7: Add indexes (if not already created)
    result = connection.execute(sa.text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'projects' 
        AND indexname = 'ix_projects_created_by_membership_id'
    """))
    projects_idx_exists = result.fetchone() is not None
    
    if not projects_idx_exists:
        op.create_index('ix_projects_created_by_membership_id', 'projects', ['created_by_membership_id'], unique=False)
    
    result = connection.execute(sa.text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'controls' 
        AND indexname = 'ix_controls_created_by_membership_id'
    """))
    controls_idx_exists = result.fetchone() is not None
    
    if not controls_idx_exists:
        op.create_index('ix_controls_created_by_membership_id', 'controls', ['created_by_membership_id'], unique=False)


def downgrade() -> None:
    """Remove created_by_membership_id from projects and controls."""
    connection = op.get_bind()
    
    # Check if indexes exist before dropping
    result = connection.execute(sa.text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'controls' 
        AND indexname = 'ix_controls_created_by_membership_id'
    """))
    if result.fetchone():
        op.drop_index('ix_controls_created_by_membership_id', table_name='controls')
    
    result = connection.execute(sa.text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'projects' 
        AND indexname = 'ix_projects_created_by_membership_id'
    """))
    if result.fetchone():
        op.drop_index('ix_projects_created_by_membership_id', table_name='projects')
    
    # Check if constraints exist before dropping
    result = connection.execute(sa.text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'controls' 
        AND constraint_name = 'fk_controls_created_by_membership_id'
    """))
    if result.fetchone():
        op.drop_constraint('fk_controls_created_by_membership_id', 'controls', type_='foreignkey')
    
    result = connection.execute(sa.text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'projects' 
        AND constraint_name = 'fk_projects_created_by_membership_id'
    """))
    if result.fetchone():
        op.drop_constraint('fk_projects_created_by_membership_id', 'projects', type_='foreignkey')
    
    # Check if columns exist before dropping
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'controls' 
        AND column_name = 'created_by_membership_id'
    """))
    if result.fetchone():
        op.drop_column('controls', 'created_by_membership_id')
    
    result = connection.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'projects' 
        AND column_name = 'created_by_membership_id'
    """))
    if result.fetchone():
        op.drop_column('projects', 'created_by_membership_id')
