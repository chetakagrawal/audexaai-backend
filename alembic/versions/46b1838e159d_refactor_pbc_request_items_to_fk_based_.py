"""refactor_pbc_request_items_to_fk_based_scope

Revision ID: 46b1838e159d
Revises: 6a8f41add7bd
Create Date: 2025-12-26 11:31:45.773809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46b1838e159d'
down_revision: Union[str, Sequence[str], None] = '6a8f41add7bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Refactor PBC request items to use FK-based entity references instead of string identifiers.

    Changes:
    - Add control_id column as alternative to project_control_id
    - Make all FK columns nullable to support flexible entity referencing
    - Add unique constraint to prevent duplicate line items
    - Add index for control_id lookups
    """
    # Add control_id column
    op.add_column('pbc_request_items', sa.Column('control_id', sa.dialects.postgresql.UUID(), nullable=True))
    op.create_foreign_key(
        'pbc_request_items_control_id_fkey',
        'pbc_request_items', 'controls',
        ['control_id'], ['id'],
        ondelete='RESTRICT'
    )

    # Make existing FK columns nullable
    op.alter_column('pbc_request_items', 'project_control_id', nullable=True)
    op.alter_column('pbc_request_items', 'application_id', nullable=True)
    op.alter_column('pbc_request_items', 'test_attribute_id', nullable=True)

    # Add index for control_id
    op.create_index('ix_pbc_request_items_control_id', 'pbc_request_items', ['control_id'])

    # Create unique partial index for active line items (excluding soft-deleted)
    # This ensures no duplicate (tenant, request, control, application, test_attribute) combinations
    op.execute(sa.text("""
        CREATE UNIQUE INDEX ux_pbc_request_items_active_entities
        ON pbc_request_items (
            tenant_id,
            pbc_request_id,
            COALESCE(project_control_id, control_id),
            application_id,
            test_attribute_id
        )
        WHERE deleted_at IS NULL
    """))


def downgrade() -> None:
    """Revert PBC request items FK-based refactoring.

    Reverts to required FK columns (not nullable) and removes control_id alternative.
    """
    # Drop unique index
    op.drop_index('ux_pbc_request_items_active_entities', table_name='pbc_request_items')

    # Drop control_id index and column
    op.drop_index('ix_pbc_request_items_control_id', table_name='pbc_request_items')
    op.drop_constraint('pbc_request_items_control_id_fkey', 'pbc_request_items', type_='foreignkey')
    op.drop_column('pbc_request_items', 'control_id')

    # Make FK columns NOT NULL again (this assumes all data is populated)
    op.alter_column('pbc_request_items', 'project_control_id', nullable=False)
    op.alter_column('pbc_request_items', 'application_id', nullable=False)
    op.alter_column('pbc_request_items', 'test_attribute_id', nullable=False)
