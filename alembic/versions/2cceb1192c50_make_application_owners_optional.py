"""make_application_owners_optional

Revision ID: 2cceb1192c50
Revises: e5723f6c198a
Create Date: 2025-12-14 21:13:17.545712

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cceb1192c50'
down_revision: Union[str, Sequence[str], None] = 'e5723f6c198a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - make business_owner_membership_id and it_owner_membership_id nullable."""
    # Alter business_owner_membership_id to be nullable
    op.alter_column('applications', 'business_owner_membership_id',
                    existing_type=sa.UUID(),
                    nullable=True)
    
    # Alter it_owner_membership_id to be nullable
    op.alter_column('applications', 'it_owner_membership_id',
                    existing_type=sa.UUID(),
                    nullable=True)


def downgrade() -> None:
    """Downgrade schema - make business_owner_membership_id and it_owner_membership_id non-nullable."""
    # Note: This will fail if there are any NULL values in these columns
    # Alter business_owner_membership_id to be non-nullable
    op.alter_column('applications', 'business_owner_membership_id',
                    existing_type=sa.UUID(),
                    nullable=False)
    
    # Alter it_owner_membership_id to be non-nullable
    op.alter_column('applications', 'it_owner_membership_id',
                    existing_type=sa.UUID(),
                    nullable=False)
