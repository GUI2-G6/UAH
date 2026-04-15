"""align saved jobs schema

Revision ID: 20260415_02
Revises: 20260415_01
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20260415_02"
down_revision = "20260415_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("saved_jobs", "job_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("saved_jobs", "url", existing_type=sa.String(length=255), type_=sa.Text(), existing_nullable=False)


def downgrade() -> None:
    op.alter_column("saved_jobs", "url", existing_type=sa.Text(), type_=sa.String(length=255), existing_nullable=False)
    op.alter_column("saved_jobs", "job_id", existing_type=sa.Integer(), nullable=False)
