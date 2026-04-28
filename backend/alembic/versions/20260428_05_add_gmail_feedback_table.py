"""add gmail feedback table

Revision ID: 20260428_05
Revises: 20260428_04
Create Date: 2026-04-28 19:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260428_05"
down_revision = "20260428_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gmail_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("sender_domain", sa.String(length=255), nullable=True),
        sa.Column("subject_key", sa.String(length=255), nullable=True),
        sa.Column("company_key", sa.String(length=255), nullable=True),
        sa.Column("triage_label", sa.String(length=40), nullable=False),
        sa.Column("override_status", sa.String(length=40), nullable=True),
        sa.Column("false_positive_reason", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gmail_feedback_id"), "gmail_feedback", ["id"], unique=False)
    op.create_index(op.f("ix_gmail_feedback_user_id"), "gmail_feedback", ["user_id"], unique=False)
    op.create_index(op.f("ix_gmail_feedback_source_id"), "gmail_feedback", ["source_id"], unique=False)
    op.create_index(op.f("ix_gmail_feedback_sender_domain"), "gmail_feedback", ["sender_domain"], unique=False)
    op.create_index(op.f("ix_gmail_feedback_subject_key"), "gmail_feedback", ["subject_key"], unique=False)
    op.create_index(op.f("ix_gmail_feedback_company_key"), "gmail_feedback", ["company_key"], unique=False)
    op.create_index(op.f("ix_gmail_feedback_triage_label"), "gmail_feedback", ["triage_label"], unique=False)
    op.create_index(op.f("ix_gmail_feedback_override_status"), "gmail_feedback", ["override_status"], unique=False)
    op.create_index(op.f("ix_gmail_feedback_created_at"), "gmail_feedback", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_gmail_feedback_created_at"), table_name="gmail_feedback")
    op.drop_index(op.f("ix_gmail_feedback_override_status"), table_name="gmail_feedback")
    op.drop_index(op.f("ix_gmail_feedback_triage_label"), table_name="gmail_feedback")
    op.drop_index(op.f("ix_gmail_feedback_company_key"), table_name="gmail_feedback")
    op.drop_index(op.f("ix_gmail_feedback_subject_key"), table_name="gmail_feedback")
    op.drop_index(op.f("ix_gmail_feedback_sender_domain"), table_name="gmail_feedback")
    op.drop_index(op.f("ix_gmail_feedback_source_id"), table_name="gmail_feedback")
    op.drop_index(op.f("ix_gmail_feedback_user_id"), table_name="gmail_feedback")
    op.drop_index(op.f("ix_gmail_feedback_id"), table_name="gmail_feedback")
    op.drop_table("gmail_feedback")
