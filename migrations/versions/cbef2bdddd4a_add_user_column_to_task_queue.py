"""add user column to task_queue

Revision ID: cbef2bdddd4a
Revises: b9d0f6473a6a
Create Date: 2026-02-25 06:58:45.694509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cbef2bdddd4a'
down_revision: Union[str, Sequence[str], None] = 'b9d0f6473a6a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        ALTER TABLE task_queue
        ADD COLUMN username TEXT;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        ALTER TABLE task_queue
        DROP COLUMN username;
    """)
