"""migrate_pbc_requests_to_v2

Revision ID: m1n2o3p4q5r6
Revises: d46d61482b1f
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'm1n2o3p4q5r6'
down_revision: Union[str, Sequence[str], None] = '9474925b2b07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Migrate pbc_requests to v2 and create pbc_request_items table."""
    
    # Step 1: Drop old indexes and foreign keys on pbc_requests (if they exist)
    # Use IF EXISTS to handle cases where indexes might not exist
    indexes_to_drop = [
        'ix_pbc_requests_tenant_id_status',
        'ix_pbc_requests_tenant_id_project_id',
        'ix_pbc_requests_tenant_id_id',
        'ix_pbc_requests_owner_membership_id',
        'ix_pbc_requests_control_id',
        'ix_pbc_requests_application_id',
        'ix_pbc_requests_project_id',
        'ix_pbc_requests_tenant_id',
        'ix_pbc_requests_id',
    ]
    
    for index_name in indexes_to_drop:
        op.execute(sa.text(f"DROP INDEX IF EXISTS {index_name}"))
    
    # Drop old foreign key constraints if they exist
    constraints_to_drop = [
        'pbc_requests_owner_membership_id_fkey',
        'pbc_requests_control_id_fkey',
        'pbc_requests_application_id_fkey',
    ]
    
    for constraint_name in constraints_to_drop:
        op.execute(sa.text(f"ALTER TABLE pbc_requests DROP CONSTRAINT IF EXISTS {constraint_name}"))
    
    # Step 2: Drop old columns from pbc_requests
    op.drop_column('pbc_requests', 'owner_membership_id')
    op.drop_column('pbc_requests', 'control_id')
    op.drop_column('pbc_requests', 'application_id')
    op.drop_column('pbc_requests', 'samples_requested')
    
    # Step 3: Add new columns to pbc_requests
    # First add as nullable, then we'll populate and make NOT NULL
    op.add_column('pbc_requests', sa.Column('instructions', sa.Text(), nullable=True))
    op.add_column('pbc_requests', sa.Column('created_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('pbc_requests', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('pbc_requests', sa.Column('updated_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('pbc_requests', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('pbc_requests', sa.Column('deleted_by_membership_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('pbc_requests', sa.Column('row_version', sa.Integer(), nullable=True))
    
    # Populate created_by_membership_id from a default membership (for existing rows)
    # In dev, we can use a placeholder or require manual migration
    # For now, we'll make it nullable and let the app handle it
    # But the model requires it, so we need to handle this
    # Option: Get first membership for each tenant and use that
    # For simplicity in dev, we'll make it nullable=False after populating
    # But since this is a breaking change, let's just make it nullable for migration
    # and require it in application code
    
    # Populate created_by_membership_id for existing rows
    # Get first membership for each tenant
    op.execute(sa.text("""
        UPDATE pbc_requests pr
        SET created_by_membership_id = (
            SELECT ut.id 
            FROM user_tenants ut 
            WHERE ut.tenant_id = pr.tenant_id 
            LIMIT 1
        )
        WHERE created_by_membership_id IS NULL
    """))
    
    # Now make it NOT NULL
    op.alter_column('pbc_requests', 'created_by_membership_id', nullable=False)
    op.alter_column('pbc_requests', 'row_version', nullable=False, server_default='1')
    
    # Update status default to 'draft'
    op.alter_column('pbc_requests', 'status', server_default='draft')
    
    # Step 4: Add foreign keys for audit fields
    op.create_foreign_key(
        'pbc_requests_created_by_membership_id_fkey',
        'pbc_requests', 'user_tenants',
        ['created_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'pbc_requests_updated_by_membership_id_fkey',
        'pbc_requests', 'user_tenants',
        ['updated_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    op.create_foreign_key(
        'pbc_requests_deleted_by_membership_id_fkey',
        'pbc_requests', 'user_tenants',
        ['deleted_by_membership_id'], ['id'],
        ondelete='RESTRICT'
    )
    
    # Step 5: Create new indexes for pbc_requests
    op.create_index('ix_pbc_requests_id', 'pbc_requests', ['id'], unique=False)
    op.create_index('ix_pbc_requests_tenant_id', 'pbc_requests', ['tenant_id'], unique=False)
    op.create_index('ix_pbc_requests_project_id', 'pbc_requests', ['project_id'], unique=False)
    op.create_index('ix_pbc_requests_created_by_membership_id', 'pbc_requests', ['created_by_membership_id'], unique=False)
    op.create_index('ix_pbc_requests_updated_by_membership_id', 'pbc_requests', ['updated_by_membership_id'], unique=False)
    op.create_index('ix_pbc_requests_deleted_by_membership_id', 'pbc_requests', ['deleted_by_membership_id'], unique=False)
    op.create_index('ix_pbc_requests_tenant_project', 'pbc_requests', ['tenant_id', 'project_id'], unique=False)
    op.create_index('ix_pbc_requests_status', 'pbc_requests', ['status'], unique=False)
    op.create_index('ix_pbc_requests_deleted_at', 'pbc_requests', ['deleted_at'], unique=False)
    
    # Step 6: Create pbc_request_items table
    op.create_table('pbc_request_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pbc_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_control_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('test_attribute_id', postgresql.UUID(as_uuid=True), nullable=False),
        # Snapshot fields
        sa.Column('pinned_control_version_num', sa.Integer(), nullable=False),
        sa.Column('pinned_test_attribute_version_num', sa.Integer(), nullable=False),
        sa.Column('effective_procedure_snapshot', sa.Text(), nullable=True),
        sa.Column('effective_evidence_snapshot', sa.Text(), nullable=True),
        sa.Column('source_snapshot', sa.String(length=50), nullable=False),
        sa.Column('override_id_snapshot', postgresql.UUID(as_uuid=True), nullable=True),
        # Workflow fields
        sa.Column('status', sa.String(length=50), nullable=False, server_default='not_started'),
        sa.Column('assignee_membership_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('instructions_extra', sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(['pbc_request_id'], ['pbc_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_control_id'], ['project_controls.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['test_attribute_id'], ['test_attributes.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['assignee_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['updated_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['deleted_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
        comment='PBC request line items with snapshot semantics'
    )
    
    # Create indexes for pbc_request_items (if they don't exist)
    item_indexes_to_create = [
        ('ix_pbc_request_items_id', ['id']),
        ('ix_pbc_request_items_tenant_id', ['tenant_id']),
        ('ix_pbc_request_items_project_id', ['project_id']),
        ('ix_pbc_request_items_pbc_request_id', ['pbc_request_id']),
        ('ix_pbc_request_items_project_control_id', ['project_control_id']),
        ('ix_pbc_request_items_application_id', ['application_id']),
        ('ix_pbc_request_items_test_attribute_id', ['test_attribute_id']),
        ('ix_pbc_request_items_assignee_membership_id', ['assignee_membership_id']),
        ('ix_pbc_request_items_created_by_membership_id', ['created_by_membership_id']),
        ('ix_pbc_request_items_updated_by_membership_id', ['updated_by_membership_id']),
        ('ix_pbc_request_items_deleted_by_membership_id', ['deleted_by_membership_id']),
        ('ix_pbc_request_items_tenant_project_request', ['tenant_id', 'project_id', 'pbc_request_id']),
        ('ix_pbc_request_items_tenant_project_control', ['tenant_id', 'project_control_id']),
        ('ix_pbc_request_items_tenant_test_attribute', ['tenant_id', 'test_attribute_id']),
        ('ix_pbc_request_items_deleted_at', ['deleted_at']),
    ]
    
    for index_name, columns in item_indexes_to_create:
        op.execute(sa.text(f"CREATE INDEX IF NOT EXISTS {index_name} ON pbc_request_items ({', '.join(columns)})"))
    
    # Create unique constraint to prevent duplicates within same request
    op.execute(sa.text("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_pbc_request_items_active
        ON pbc_request_items (tenant_id, pbc_request_id, project_control_id, application_id, test_attribute_id)
        WHERE deleted_at IS NULL
    """))
    
    # Update comment on pbc_requests table
    op.alter_column('pbc_requests', 'id', comment='PBC requests v2 - containers for evidence collection requests')


def downgrade() -> None:
    """Revert pbc_requests v2 migration."""
    
    # Drop pbc_request_items table
    op.drop_index('ux_pbc_request_items_active', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_deleted_at', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_tenant_test_attribute', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_tenant_project_control', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_tenant_project_request', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_deleted_by_membership_id', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_updated_by_membership_id', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_created_by_membership_id', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_assignee_membership_id', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_test_attribute_id', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_application_id', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_project_control_id', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_pbc_request_id', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_project_id', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_tenant_id', table_name='pbc_request_items')
    op.drop_index('ix_pbc_request_items_id', table_name='pbc_request_items')
    op.drop_table('pbc_request_items')
    
    # Revert pbc_requests changes
    op.drop_index('ix_pbc_requests_deleted_at', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_status', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_tenant_project', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_deleted_by_membership_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_updated_by_membership_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_created_by_membership_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_project_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_tenant_id', table_name='pbc_requests')
    op.drop_index('ix_pbc_requests_id', table_name='pbc_requests')
    
    op.drop_constraint('pbc_requests_deleted_by_membership_id_fkey', 'pbc_requests', type_='foreignkey')
    op.drop_constraint('pbc_requests_updated_by_membership_id_fkey', 'pbc_requests', type_='foreignkey')
    op.drop_constraint('pbc_requests_created_by_membership_id_fkey', 'pbc_requests', type_='foreignkey')
    
    op.drop_column('pbc_requests', 'row_version')
    op.drop_column('pbc_requests', 'deleted_by_membership_id')
    op.drop_column('pbc_requests', 'deleted_at')
    op.drop_column('pbc_requests', 'updated_by_membership_id')
    op.drop_column('pbc_requests', 'updated_at')
    op.drop_column('pbc_requests', 'created_by_membership_id')
    op.drop_column('pbc_requests', 'instructions')
    
    op.add_column('pbc_requests', sa.Column('samples_requested', sa.Integer(), nullable=True))
    op.add_column('pbc_requests', sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("'00000000-0000-0000-0000-000000000000'::uuid")))
    op.add_column('pbc_requests', sa.Column('control_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("'00000000-0000-0000-0000-000000000000'::uuid")))
    op.add_column('pbc_requests', sa.Column('owner_membership_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("'00000000-0000-0000-0000-000000000000'::uuid")))
    
    op.create_foreign_key('pbc_requests_application_id_fkey', 'pbc_requests', 'applications', ['application_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('pbc_requests_control_id_fkey', 'pbc_requests', 'controls', ['control_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('pbc_requests_owner_membership_id_fkey', 'pbc_requests', 'user_tenants', ['owner_membership_id'], ['id'], ondelete='CASCADE')
    
    op.create_index('ix_pbc_requests_id', 'pbc_requests', ['id'], unique=False)
    op.create_index('ix_pbc_requests_tenant_id', 'pbc_requests', ['tenant_id'], unique=False)
    op.create_index('ix_pbc_requests_project_id', 'pbc_requests', ['project_id'], unique=False)
    op.create_index('ix_pbc_requests_application_id', 'pbc_requests', ['application_id'], unique=False)
    op.create_index('ix_pbc_requests_control_id', 'pbc_requests', ['control_id'], unique=False)
    op.create_index('ix_pbc_requests_owner_membership_id', 'pbc_requests', ['owner_membership_id'], unique=False)
    op.create_index('ix_pbc_requests_tenant_id_id', 'pbc_requests', ['tenant_id', 'id'], unique=False)
    op.create_index('ix_pbc_requests_tenant_id_project_id', 'pbc_requests', ['tenant_id', 'project_id'], unique=False)
    op.create_index('ix_pbc_requests_tenant_id_status', 'pbc_requests', ['tenant_id', 'status'], unique=False)
    
    op.alter_column('pbc_requests', 'status', server_default='pending')

