"""add explicit composite index on controls tenant_id control_code

Revision ID: d28a462d63d7
Revises: 5d8a2a7af60d
Create Date: 2025-12-13 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd28a462d63d7'
down_revision: Union[str, Sequence[str], None] = '5d8a2a7af60d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add explicit composite index on (tenant_id, control_code) for query optimization."""
    
    # Note: A unique constraint already exists on (tenant_id, control_code) which creates an index
    # This explicit index is for clarity and to ensure optimal query performance
    # PostgreSQL will use the unique constraint's index, but having an explicit one is good practice
    
    # Check if index already exists (it might from the unique constraint)
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'controls' 
        AND indexname = 'ix_controls_tenant_id_control_code'
    """))
    index_exists = result.fetchone() is not None
    
    if not index_exists:
        # Create explicit composite index for query optimization
        op.create_index(
            'ix_controls_tenant_id_control_code',
            'controls',
            ['tenant_id', 'control_code'],
            unique=False  # Not unique (unique constraint already exists)
        )


def downgrade() -> None:
    """Remove explicit composite index."""
    connection = op.get_bind()
    
    # Check if index exists before dropping
    result = connection.execute(sa.text("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = 'controls' 
        AND indexname = 'ix_controls_tenant_id_control_code'
    """))
    if result.fetchone():
        op.drop_index('ix_controls_tenant_id_control_code', table_name='controls')
