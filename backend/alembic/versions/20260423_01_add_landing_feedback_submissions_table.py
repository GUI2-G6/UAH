"""add landing feedback submissions table

Revision ID: 20260423_01
Revises: 20260422_01
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20260423_01"
down_revision = "20260422_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "landing_feedback_submissions" not in existing_tables:
        op.create_table(
            "landing_feedback_submissions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("full_name", sa.String(length=120), nullable=True),
            sa.Column("frustration", sa.Text(), nullable=True),
            sa.Column("features", sa.Text(), nullable=True),
            sa.Column("notify_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("interested_beta", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("source_surface", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("landing_feedback_submissions")}
    if "ix_landing_feedback_submissions_email" not in indexes:
        op.create_index(
            "ix_landing_feedback_submissions_email",
            "landing_feedback_submissions",
            ["email"],
            unique=False,
        )
    if "ix_landing_feedback_submissions_created_at" not in indexes:
        op.create_index(
            "ix_landing_feedback_submissions_created_at",
            "landing_feedback_submissions",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "landing_feedback_submissions" not in existing_tables:
        return

    indexes = {index["name"] for index in inspector.get_indexes("landing_feedback_submissions")}
    if "ix_landing_feedback_submissions_created_at" in indexes:
        op.drop_index("ix_landing_feedback_submissions_created_at", table_name="landing_feedback_submissions")
    if "ix_landing_feedback_submissions_email" in indexes:
        op.drop_index("ix_landing_feedback_submissions_email", table_name="landing_feedback_submissions")

    op.drop_table("landing_feedback_submissions")
