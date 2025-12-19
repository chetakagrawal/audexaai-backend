"""make_updated_at_nullable_on_creation

Revision ID: a95a6bf8fc4b
Revises: g9h0i1j2k3l4
Create Date: 2025-12-19 14:33:27.245346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a95a6bf8fc4b'
down_revision: Union[str, Sequence[str], None] = 'g9h0i1j2k3l4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make updated_at nullable in controls and applications tables.
    
    This allows updated_at to be NULL on creation, and only be set when
    a record is actually updated. This provides clearer semantics:
    - NULL = never updated
    - Non-NULL = last update timestamp
    """
    # Make updated_at nullable in controls table and remove default
    op.alter_column('controls', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=True,
                    existing_nullable=False,
                    server_default=None)
    
    # Make updated_at nullable in applications table and remove default
    op.alter_column('applications', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=True,
                    existing_nullable=False,
                    server_default=None)


def downgrade() -> None:
    """Revert updated_at to NOT NULL (with default value on creation)."""
    # Set any NULL values to created_at before making column NOT NULL
    # For controls
    op.execute("""
        UPDATE controls 
        SET updated_at = created_at 
        WHERE updated_at IS NULL
    """)
    
    # For applications
    op.execute("""
        UPDATE applications 
        SET updated_at = created_at 
        WHERE updated_at IS NULL
    """)
    
    # Make updated_at NOT NULL again
    op.alter_column('controls', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False,
                    existing_nullable=True)
    
    op.alter_column('applications', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    nullable=False,
                    existing_nullable=True)
