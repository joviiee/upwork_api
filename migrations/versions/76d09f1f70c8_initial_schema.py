"""initial schema

Revision ID: 76d09f1f70c8
Revises: 
Create Date: 2026-02-19 08:48:32.080289

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76d09f1f70c8'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # USERS
    op.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)

    # JOBS
    op.execute("""
        CREATE TABLE jobs (
            id SERIAL PRIMARY KEY,
            job_uuid BIGINT UNIQUE,
            job_url TEXT NOT NULL UNIQUE,
            job_title TEXT,
            job_description JSONB NOT NULL,
            proposal_generation_status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)

    op.execute("""
        CREATE INDEX idx_jobs_proposal_status
        ON jobs (proposal_generation_status);
    """)

    # PROPOSALS
    op.execute("""
        CREATE TABLE proposals (
            id SERIAL PRIMARY KEY,
            job_uuid BIGINT UNIQUE,
            job_url TEXT NOT NULL UNIQUE,
            job_type TEXT,
            proposal JSONB NOT NULL,
            applied BOOLEAN NOT NULL DEFAULT FALSE,
            approved_by TEXT,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)

    # TASK QUEUE
    op.execute("""
        CREATE TABLE task_queue (
            id SERIAL PRIMARY KEY,
            task_type TEXT NOT NULL,
            payload JSONB,
            priority INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
    """)

    op.execute("""
        CREATE INDEX idx_task_queue_priority
        ON task_queue (priority DESC, created_at);
    """)

    # PROMPTS
    op.execute("""
        CREATE TABLE prompts (
            id SERIAL PRIMARY KEY,
            prompt_name TEXT NOT NULL,
            version INTEGER NOT NULL,
            prompt_text TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            is_active BOOLEAN DEFAULT FALSE,
            UNIQUE (prompt_name, version)
        );
    """)

    op.execute("""
        CREATE INDEX idx_prompts_name_active
        ON prompts (prompt_name, is_active);
    """)


def downgrade() -> None:
    """Downgrade schema."""
    pass
