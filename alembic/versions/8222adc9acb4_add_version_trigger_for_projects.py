"""add_version_trigger_for_projects

Revision ID: 8222adc9acb4
Revises: 1c8c9518a387
Create Date: 2025-12-19 21:49:13.800258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8222adc9acb4'
down_revision: Union[str, Sequence[str], None] = '1c8c9518a387'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create trigger to capture project versions using the generic audit function.
    
    The generic audit_capture_entity_version() function already exists (from migration 4271a2cf3387).
    We just need to create a trigger that uses it for the projects table.
    """
    # Create trigger for projects using the generic function
    op.execute("""
        CREATE TRIGGER trigger_audit_capture_project_version
        BEFORE UPDATE OR DELETE ON projects
        FOR EACH ROW
        EXECUTE FUNCTION audit_capture_entity_version();
    """)


def downgrade() -> None:
    """Drop trigger for projects."""
    op.execute("DROP TRIGGER IF EXISTS trigger_audit_capture_project_version ON projects;")
