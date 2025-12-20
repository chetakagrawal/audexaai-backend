"""add_description_to_controls

Revision ID: 08086e84d319
Revises: aa1e5d0a0361
Create Date: 2025-12-19 21:15:46.238050

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '08086e84d319'
down_revision: Union[str, Sequence[str], None] = 'aa1e5d0a0361'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add description column to controls table."""
    op.add_column('controls', sa.Column('description', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove description column from controls table."""
    op.drop_column('controls', 'description')
