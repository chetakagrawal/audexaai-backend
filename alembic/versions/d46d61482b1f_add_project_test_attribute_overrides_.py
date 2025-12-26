"""add_project_test_attribute_overrides_table

Revision ID: d46d61482b1f
Revises: e88d93747af
Create Date: 2025-12-20 12:58:25.361261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd46d61482b1f'
down_revision: Union[str, Sequence[str], None] = 'e88d93747af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add project_test_attribute_overrides table."""
    op.create_table('project_test_attribute_overrides',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('project_control_id', sa.UUID(), nullable=False),
    sa.Column('test_attribute_id', sa.UUID(), nullable=False),
    sa.Column('application_id', sa.UUID(), nullable=True),
    sa.Column('base_test_attribute_version_num', sa.Integer(), nullable=False),
    sa.Column('name_override', sa.Text(), nullable=True),
    sa.Column('frequency_override', sa.Text(), nullable=True),
    sa.Column('procedure_override', sa.Text(), nullable=True),
    sa.Column('expected_evidence_override', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by_membership_id', sa.UUID(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_by_membership_id', sa.UUID(), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by_membership_id', sa.UUID(), nullable=True),
    sa.Column('row_version', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['created_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['deleted_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['project_control_id'], ['project_controls.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['test_attribute_id'], ['test_attributes.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['updated_by_membership_id'], ['user_tenants.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    comment='Project-level overrides for test attributes with tenant isolation and version freezing'
    )
    op.create_index(op.f('ix_project_test_attribute_overrides_application_id'), 'project_test_attribute_overrides', ['application_id'], unique=False)
    op.create_index(op.f('ix_project_test_attribute_overrides_created_by_membership_id'), 'project_test_attribute_overrides', ['created_by_membership_id'], unique=False)
    op.create_index(op.f('ix_project_test_attribute_overrides_deleted_at'), 'project_test_attribute_overrides', ['deleted_at'], unique=False)
    op.create_index(op.f('ix_project_test_attribute_overrides_deleted_by_membership_id'), 'project_test_attribute_overrides', ['deleted_by_membership_id'], unique=False)
    op.create_index(op.f('ix_project_test_attribute_overrides_id'), 'project_test_attribute_overrides', ['id'], unique=False)
    op.create_index(op.f('ix_project_test_attribute_overrides_project_control_id'), 'project_test_attribute_overrides', ['project_control_id'], unique=False)
    op.create_index(op.f('ix_project_test_attribute_overrides_tenant_id'), 'project_test_attribute_overrides', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_project_test_attribute_overrides_test_attribute_id'), 'project_test_attribute_overrides', ['test_attribute_id'], unique=False)
    op.create_index(op.f('ix_project_test_attribute_overrides_updated_by_membership_id'), 'project_test_attribute_overrides', ['updated_by_membership_id'], unique=False)
    op.create_index('ix_ptao_tenant_project_control', 'project_test_attribute_overrides', ['tenant_id', 'project_control_id'], unique=False)
    op.create_index('ix_ptao_tenant_test_attribute', 'project_test_attribute_overrides', ['tenant_id', 'test_attribute_id'], unique=False)
    op.create_index('ux_ptao_active_app', 'project_test_attribute_overrides', ['tenant_id', 'project_control_id', 'application_id', 'test_attribute_id'], unique=True, postgresql_where=sa.text('deleted_at IS NULL AND application_id IS NOT NULL'))
    op.create_index('ux_ptao_active_global', 'project_test_attribute_overrides', ['tenant_id', 'project_control_id', 'test_attribute_id'], unique=True, postgresql_where=sa.text('deleted_at IS NULL AND application_id IS NULL'))
    
    # Ensure the generic version trigger function exists (should already exist from earlier migration, but create if missing)
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_capture_entity_version()
        RETURNS TRIGGER AS $$
        DECLARE
            v_operation TEXT;
            v_changed_by_membership_id UUID;
            v_entity_type TEXT;
        BEGIN
            -- Determine entity_type from table name
            v_entity_type := TG_TABLE_NAME;
            
            -- Determine operation
            IF TG_OP = 'DELETE' THEN
                v_operation := 'DELETE';
                v_changed_by_membership_id := NULL;
            ELSE
                -- UPDATE operation
                IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
                    -- Soft delete: OLD was active, NEW is deleted
                    v_operation := 'DELETE';
                    v_changed_by_membership_id := NEW.deleted_by_membership_id;
                ELSE
                    -- Regular update
                    v_operation := 'UPDATE';
                    v_changed_by_membership_id := NEW.updated_by_membership_id;
                END IF;
            END IF;
            
            -- Insert snapshot into entity_versions
            INSERT INTO entity_versions (
                tenant_id,
                entity_type,
                entity_id,
                operation,
                version_num,
                valid_from,
                valid_to,
                changed_by_membership_id,
                data
            ) VALUES (
                OLD.tenant_id,
                v_entity_type,
                OLD.id,
                v_operation,
                OLD.row_version,
                COALESCE(OLD.updated_at, OLD.created_at),
                NOW(),
                v_changed_by_membership_id,
                to_jsonb(OLD)
            );
            
            -- Return appropriate record
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            ELSE
                RETURN NEW;
            END IF;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for project_test_attribute_overrides version history
    op.execute("""
        CREATE TRIGGER trigger_audit_capture_project_test_attribute_override_version
        BEFORE UPDATE OR DELETE ON project_test_attribute_overrides
        FOR EACH ROW
        EXECUTE FUNCTION audit_capture_entity_version();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop trigger for project_test_attribute_overrides
    op.execute("DROP TRIGGER IF EXISTS trigger_audit_capture_project_test_attribute_override_version ON project_test_attribute_overrides;")
    
    op.drop_index('ux_ptao_active_global', table_name='project_test_attribute_overrides', postgresql_where=sa.text('deleted_at IS NULL AND application_id IS NULL'))
    op.drop_index('ux_ptao_active_app', table_name='project_test_attribute_overrides', postgresql_where=sa.text('deleted_at IS NULL AND application_id IS NOT NULL'))
    op.drop_index('ix_ptao_tenant_test_attribute', table_name='project_test_attribute_overrides')
    op.drop_index('ix_ptao_tenant_project_control', table_name='project_test_attribute_overrides')
    op.drop_index(op.f('ix_project_test_attribute_overrides_updated_by_membership_id'), table_name='project_test_attribute_overrides')
    op.drop_index(op.f('ix_project_test_attribute_overrides_test_attribute_id'), table_name='project_test_attribute_overrides')
    op.drop_index(op.f('ix_project_test_attribute_overrides_tenant_id'), table_name='project_test_attribute_overrides')
    op.drop_index(op.f('ix_project_test_attribute_overrides_project_control_id'), table_name='project_test_attribute_overrides')
    op.drop_index(op.f('ix_project_test_attribute_overrides_id'), table_name='project_test_attribute_overrides')
    op.drop_index(op.f('ix_project_test_attribute_overrides_deleted_by_membership_id'), table_name='project_test_attribute_overrides')
    op.drop_index(op.f('ix_project_test_attribute_overrides_deleted_at'), table_name='project_test_attribute_overrides')
    op.drop_index(op.f('ix_project_test_attribute_overrides_created_by_membership_id'), table_name='project_test_attribute_overrides')
    op.drop_index(op.f('ix_project_test_attribute_overrides_application_id'), table_name='project_test_attribute_overrides')
    op.drop_table('project_test_attribute_overrides')
