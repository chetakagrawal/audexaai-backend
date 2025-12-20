"""make_updated_at_nullable_on_test_attributes

Revision ID: h1i2j3k4l5m6
Revises: 0e5efd57ffaf
Create Date: 2025-12-20 04:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h1i2j3k4l5m6'
down_revision: Union[str, Sequence[str], None] = '0e5efd57ffaf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make updated_at nullable in test_attributes table.
    
    This allows updated_at to be NULL on creation, and only be set when
    a record is actually updated. This provides clearer semantics:
    - NULL = never updated
    - Non-NULL = last update timestamp
    
    This matches the pattern used in controls and applications tables.
    """
    # Make updated_at nullable in test_attributes table and remove default
    op.alter_column('test_attributes', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=True,
                    existing_nullable=False,
                    server_default=None)


def downgrade() -> None:
    """Revert updated_at to NOT NULL (with default value on creation)."""
    # Set any NULL values to created_at before making column NOT NULL
    op.execute("""
        UPDATE test_attributes 
        SET updated_at = created_at 
        WHERE updated_at IS NULL
    """)
    
    # Make updated_at NOT NULL again
    op.alter_column('test_attributes', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False,
                    existing_nullable=True)

