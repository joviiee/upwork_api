"""remove profile column in jobs and create in proposals

Revision ID: b9d0f6473a6a
Revises: 690b5af4f23e
Create Date: 2026-02-23 06:23:05.620508

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9d0f6473a6a'
down_revision: Union[str, Sequence[str], None] = '690b5af4f23e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        ALTER TABLE jobs
        DROP COLUMN profile;
    """)
    
    op.execute("""
        ALTER TABLE proposals
        ADD COLUMN profile TEXT NOT NULL DEFAULT 'general_profile';
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        ALTER TABLE proposals
        DROP COLUMN profile;
    """)

    # Restore in jobs
    op.execute("""
        ALTER TABLE jobs
        ADD COLUMN profile TEXT NOT NULL DEFAULT 'general_profile';
    """)
