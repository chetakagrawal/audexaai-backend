"""add_control_version_trigger

Revision ID: a9b11eeb4af5
Revises: d7887576e4a5
Create Date: 2025-12-19 14:54:23.574764

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9b11eeb4af5'
down_revision: Union[str, Sequence[str], None] = 'd7887576e4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create trigger function and trigger to capture control versions."""
    # Create PL/pgSQL function to capture OLD row snapshots
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
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER trigger_audit_capture_control_version
        BEFORE UPDATE OR DELETE ON controls
        FOR EACH ROW
        EXECUTE FUNCTION audit_capture_control_version();
    """)


def downgrade() -> None:
    """Drop trigger and function."""
    op.execute("DROP TRIGGER IF EXISTS trigger_audit_capture_control_version ON controls;")
    op.execute("DROP FUNCTION IF EXISTS audit_capture_control_version();")
