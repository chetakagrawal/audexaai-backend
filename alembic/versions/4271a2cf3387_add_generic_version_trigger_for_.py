"""add_generic_version_trigger_for_applications

Revision ID: 4271a2cf3387
Revises: a9b11eeb4af5
Create Date: 2025-12-19 15:26:12.734409

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4271a2cf3387'
down_revision: Union[str, Sequence[str], None] = 'a9b11eeb4af5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Refactor trigger function to be generic and add trigger for applications."""
    # Drop the old control-specific function
    op.execute("DROP FUNCTION IF EXISTS audit_capture_control_version() CASCADE;")
    
    # Create generic trigger function that works for any table with the standard audit fields
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
                v_changed_by_membership_id := NULL;  -- OLD doesn't have NEW fields
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
    
    # Drop old control trigger and recreate with generic function
    op.execute("DROP TRIGGER IF EXISTS trigger_audit_capture_control_version ON controls;")
    op.execute("""
        CREATE TRIGGER trigger_audit_capture_control_version
        BEFORE UPDATE OR DELETE ON controls
        FOR EACH ROW
        EXECUTE FUNCTION audit_capture_entity_version();
    """)
    
    # Create trigger for applications
    op.execute("""
        CREATE TRIGGER trigger_audit_capture_application_version
        BEFORE UPDATE OR DELETE ON applications
        FOR EACH ROW
        EXECUTE FUNCTION audit_capture_entity_version();
    """)


def downgrade() -> None:
    """Drop application trigger and revert to control-specific function."""
    # Drop application trigger
    op.execute("DROP TRIGGER IF EXISTS trigger_audit_capture_application_version ON applications;")
    
    # Drop generic function
    op.execute("DROP FUNCTION IF EXISTS audit_capture_entity_version() CASCADE;")
    
    # Recreate control-specific function (from previous migration)
    op.execute("""
        CREATE OR REPLACE FUNCTION audit_capture_control_version()
        RETURNS TRIGGER AS $$
        DECLARE
            v_operation TEXT;
            v_changed_by_membership_id UUID;
        BEGIN
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
                'controls',
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
    
    # Recreate control trigger
    op.execute("""
        CREATE TRIGGER trigger_audit_capture_control_version
        BEFORE UPDATE OR DELETE ON controls
        FOR EACH ROW
        EXECUTE FUNCTION audit_capture_control_version();
    """)
