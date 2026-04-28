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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "resumes" not in set(inspector.get_table_names()):
        return
    existing = {c["name"] for c in inspector.get_columns("resumes")}
    if "raw_markdown_source" not in existing:
        op.add_column("resumes", sa.Column("raw_markdown_source", sa.String(length=80), nullable=True))
    if "raw_markdown_method" not in existing:
        op.add_column("resumes", sa.Column("raw_markdown_method", sa.String(length=50), nullable=True))
    if "raw_markdown_updated_at" not in existing:
        op.add_column("resumes", sa.Column("raw_markdown_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "resumes" not in set(inspector.get_table_names()):
        return
    existing = {c["name"] for c in inspector.get_columns("resumes")}
    if "raw_markdown_updated_at" in existing:
        op.drop_column("resumes", "raw_markdown_updated_at")
    if "raw_markdown_method" in existing:
        op.drop_column("resumes", "raw_markdown_method")
    if "raw_markdown_source" in existing:
        op.drop_column("resumes", "raw_markdown_source")
