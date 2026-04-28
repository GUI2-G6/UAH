"""add gmail notification states table

Revision ID: 20260428_03
Revises: 20260428_02
Create Date: 2026-04-28 18:03:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260428_03"
down_revision = "20260428_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gmail_notification_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("snoozed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_id", name="uq_gmail_notification_states_user_source"),
    )
    op.create_index(op.f("ix_gmail_notification_states_id"), "gmail_notification_states", ["id"], unique=False)
    op.create_index(op.f("ix_gmail_notification_states_user_id"), "gmail_notification_states", ["user_id"], unique=False)
    op.create_index(op.f("ix_gmail_notification_states_source_id"), "gmail_notification_states", ["source_id"], unique=False)
    op.create_index(op.f("ix_gmail_notification_states_state"), "gmail_notification_states", ["state"], unique=False)
    op.create_index(op.f("ix_gmail_notification_states_snoozed_until"), "gmail_notification_states", ["snoozed_until"], unique=False)
    op.create_index(op.f("ix_gmail_notification_states_created_at"), "gmail_notification_states", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_gmail_notification_states_created_at"), table_name="gmail_notification_states")
    op.drop_index(op.f("ix_gmail_notification_states_snoozed_until"), table_name="gmail_notification_states")
    op.drop_index(op.f("ix_gmail_notification_states_state"), table_name="gmail_notification_states")
    op.drop_index(op.f("ix_gmail_notification_states_source_id"), table_name="gmail_notification_states")
    op.drop_index(op.f("ix_gmail_notification_states_user_id"), table_name="gmail_notification_states")
    op.drop_index(op.f("ix_gmail_notification_states_id"), table_name="gmail_notification_states")
    op.drop_table("gmail_notification_states")
