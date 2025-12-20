"""make_created_by_membership_id_not_null_on_test_attributes

Revision ID: i2j3k4l5m6n7
Revises: h1i2j3k4l5m6
Create Date: 2025-12-20 04:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'i2j3k4l5m6n7'
down_revision: Union[str, Sequence[str], None] = 'h1i2j3k4l5m6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make created_by_membership_id NOT NULL in test_attributes table.
    
    This matches the pattern used in controls table where created_by_membership_id
    is required. Test attributes always have a creator, so this should not be nullable.
    """
    # First, set any NULL values to a default (shouldn't exist, but be safe)
    # We'll use the first membership in the tenant as a fallback
    # In practice, this should never be needed since we always set it in the service
    op.execute("""
        UPDATE test_attributes ta
        SET created_by_membership_id = (
            SELECT ut.id 
            FROM user_tenants ut 
            WHERE ut.tenant_id = ta.tenant_id 
            LIMIT 1
        )
        WHERE created_by_membership_id IS NULL
        AND EXISTS (
            SELECT 1 FROM user_tenants ut WHERE ut.tenant_id = ta.tenant_id
        );
    """)
    
    # Delete any test attributes that still have NULL created_by_membership_id
    # (shouldn't happen, but if it does, they're orphaned)
    op.execute("""
        DELETE FROM test_attributes 
        WHERE created_by_membership_id IS NULL;
    """)
    
    # Make created_by_membership_id NOT NULL
    op.alter_column('test_attributes', 'created_by_membership_id',
                    existing_type=postgresql.UUID(as_uuid=True),
                    nullable=False,
                    existing_nullable=True)


def downgrade() -> None:
    """Revert created_by_membership_id to nullable."""
    op.alter_column('test_attributes', 'created_by_membership_id',
                    existing_type=postgresql.UUID(as_uuid=True),
                    nullable=True,
                    existing_nullable=False)

