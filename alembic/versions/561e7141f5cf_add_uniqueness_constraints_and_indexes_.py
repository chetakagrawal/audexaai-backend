"""add uniqueness constraints and indexes for identity and membership integrity

Revision ID: 561e7141f5cf
Revises: 8850c98ed5f8
Create Date: 2025-12-12 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '561e7141f5cf'
down_revision: Union[str, Sequence[str], None] = '8850c98ed5f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add uniqueness constraints and indexes for identity/membership integrity."""
    
    # 1. Case-insensitive unique constraint on users.primary_email
    # Drop the existing case-sensitive unique constraint/index if it exists
    op.execute("""
        DROP INDEX IF EXISTS ix_users_primary_email;
    """)
    
    # Create case-insensitive unique index
    op.execute("""
        CREATE UNIQUE INDEX ix_users_primary_email_lower 
        ON users (LOWER(primary_email));
    """)
    
    # Also create a regular index for lookups (non-unique)
    op.create_index(
        'ix_users_primary_email',
        'users',
        ['primary_email'],
        unique=False
    )
    
    # 2. Verify AuthIdentity(provider, provider_subject) UNIQUE constraint exists
    # This should already exist from previous migration, but verify
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'uq_provider_subject'
            ) THEN
                ALTER TABLE auth_identities 
                ADD CONSTRAINT uq_provider_subject 
                UNIQUE (provider, provider_subject);
            END IF;
        END $$;
    """)
    
    # 3. Verify UserTenant(tenant_id, user_id) UNIQUE constraint exists
    # This should already exist from previous migration, but verify
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = 'uq_user_tenant'
            ) THEN
                ALTER TABLE user_tenants 
                ADD CONSTRAINT uq_user_tenant 
                UNIQUE (user_id, tenant_id);
            END IF;
        END $$;
    """)
    
    # 4. Verify indexes exist (they should from previous migration, but ensure they're there)
    # UserTenant indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_user_tenants_user_id 
        ON user_tenants (user_id);
    """)
    
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_user_tenants_tenant_id 
        ON user_tenants (tenant_id);
    """)
    
    # AuthIdentity user_id index
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_auth_identities_user_id 
        ON auth_identities (user_id);
    """)


def downgrade() -> None:
    """Remove uniqueness constraints and indexes."""
    
    # Drop case-insensitive unique index
    op.execute("DROP INDEX IF EXISTS ix_users_primary_email_lower;")
    
    # Restore case-sensitive unique constraint on primary_email
    op.create_index(
        'ix_users_primary_email',
        'users',
        ['primary_email'],
        unique=True
    )
    
    # Note: We don't drop the other constraints/indexes as they may be needed
    # If you need to fully downgrade, you would drop them here:
    # op.drop_constraint('uq_provider_subject', 'auth_identities', type_='unique')
    # op.drop_constraint('uq_user_tenant', 'user_tenants', type_='unique')
