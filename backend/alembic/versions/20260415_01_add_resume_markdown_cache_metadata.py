"""add resume markdown cache metadata

Revision ID: 20260415_01
Revises: 20260413_04
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260415_01"
down_revision = "20260413_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("raw_markdown_source", sa.String(length=80), nullable=True))
    op.add_column("resumes", sa.Column("raw_markdown_method", sa.String(length=50), nullable=True))
    op.add_column("resumes", sa.Column("raw_markdown_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "raw_markdown_updated_at")
    op.drop_column("resumes", "raw_markdown_method")
    op.drop_column("resumes", "raw_markdown_source")
