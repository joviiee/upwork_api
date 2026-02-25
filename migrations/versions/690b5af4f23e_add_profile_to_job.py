"""add profile to job

Revision ID: 690b5af4f23e
Revises: 76d09f1f70c8
Create Date: 2026-02-23 05:55:49.114665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '690b5af4f23e'
down_revision: Union[str, Sequence[str], None] = '76d09f1f70c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        ALTER TABLE jobs
        ADD COLUMN profile TEXT NOT NULL DEFAULT 'general_profile';
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("""
        ALTER TABLE jobs
        DROP COLUMN profile;
    """)