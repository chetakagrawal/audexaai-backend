"""add_missing_test_attributes_version_trigger

Revision ID: aa1e5d0a0361
Revises: i2j3k4l5m6n7
Create Date: 2025-12-19 21:10:28.708337

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa1e5d0a0361'
down_revision: Union[str, Sequence[str], None] = 'i2j3k4l5m6n7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing test_attributes version trigger."""
    # First, ensure the generic function exists (from migration 4271a2cf3387)
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
    
    # Drop trigger if it exists (in case of partial migration)
    op.execute("DROP TRIGGER IF EXISTS trigger_audit_capture_test_attribute_version ON test_attributes;")
    
    # Create trigger for version history (uses existing generic function)
    op.execute("""
        CREATE TRIGGER trigger_audit_capture_test_attribute_version
        BEFORE UPDATE OR DELETE ON test_attributes
        FOR EACH ROW
        EXECUTE FUNCTION audit_capture_entity_version();
    """)


def downgrade() -> None:
    """Remove test_attributes version trigger."""
    op.execute("DROP TRIGGER IF EXISTS trigger_audit_capture_test_attribute_version ON test_attributes;")
