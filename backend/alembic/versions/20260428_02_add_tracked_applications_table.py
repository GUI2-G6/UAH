"""add tracked applications table

Revision ID: 20260428_02
Revises: 20260428_01
Create Date: 2026-04-28 17:25:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260428_02"
down_revision = "20260428_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracked_applications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("apply_session_id", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_ref", sa.String(length=255), nullable=False),
        sa.Column("thread_key", sa.String(length=500), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("job_title", sa.String(length=255), nullable=True),
        sa.Column("latest_status", sa.String(length=80), nullable=True),
        sa.Column("selection_state", sa.String(length=40), nullable=False),
        sa.Column("has_new_update", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_update_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["apply_session_id"], ["apply_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_type", "source_ref", name="uq_tracked_applications_user_source"),
    )
    op.create_index(op.f("ix_tracked_applications_id"), "tracked_applications", ["id"], unique=False)
    op.create_index(op.f("ix_tracked_applications_user_id"), "tracked_applications", ["user_id"], unique=False)
    op.create_index(op.f("ix_tracked_applications_apply_session_id"), "tracked_applications", ["apply_session_id"], unique=False)
    op.create_index(op.f("ix_tracked_applications_source_type"), "tracked_applications", ["source_type"], unique=False)
    op.create_index(op.f("ix_tracked_applications_source_ref"), "tracked_applications", ["source_ref"], unique=False)
    op.create_index(op.f("ix_tracked_applications_thread_key"), "tracked_applications", ["thread_key"], unique=False)
    op.create_index(op.f("ix_tracked_applications_selection_state"), "tracked_applications", ["selection_state"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_tracked_applications_selection_state"), table_name="tracked_applications")
    op.drop_index(op.f("ix_tracked_applications_thread_key"), table_name="tracked_applications")
    op.drop_index(op.f("ix_tracked_applications_source_ref"), table_name="tracked_applications")
    op.drop_index(op.f("ix_tracked_applications_source_type"), table_name="tracked_applications")
    op.drop_index(op.f("ix_tracked_applications_apply_session_id"), table_name="tracked_applications")
    op.drop_index(op.f("ix_tracked_applications_user_id"), table_name="tracked_applications")
    op.drop_index(op.f("ix_tracked_applications_id"), table_name="tracked_applications")
    op.drop_table("tracked_applications")
