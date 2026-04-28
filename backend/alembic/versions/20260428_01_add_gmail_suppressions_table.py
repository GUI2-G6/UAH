"""add gmail suppressions table

Revision ID: 20260428_01
Revises: 20260423_01
Create Date: 2026-04-28 16:55:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260428_01"
down_revision = "20260423_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gmail_suppressions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("sender_domain", sa.String(length=255), nullable=True),
        sa.Column("subject_key", sa.String(length=255), nullable=True),
        sa.Column("company_key", sa.String(length=255), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gmail_suppressions_id"), "gmail_suppressions", ["id"], unique=False)
    op.create_index(op.f("ix_gmail_suppressions_user_id"), "gmail_suppressions", ["user_id"], unique=False)
    op.create_index(op.f("ix_gmail_suppressions_scope"), "gmail_suppressions", ["scope"], unique=False)
    op.create_index(op.f("ix_gmail_suppressions_source_id"), "gmail_suppressions", ["source_id"], unique=False)
    op.create_index(op.f("ix_gmail_suppressions_sender_domain"), "gmail_suppressions", ["sender_domain"], unique=False)
    op.create_index(op.f("ix_gmail_suppressions_subject_key"), "gmail_suppressions", ["subject_key"], unique=False)
    op.create_index(op.f("ix_gmail_suppressions_company_key"), "gmail_suppressions", ["company_key"], unique=False)
    op.create_index(op.f("ix_gmail_suppressions_created_at"), "gmail_suppressions", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_gmail_suppressions_created_at"), table_name="gmail_suppressions")
    op.drop_index(op.f("ix_gmail_suppressions_company_key"), table_name="gmail_suppressions")
    op.drop_index(op.f("ix_gmail_suppressions_subject_key"), table_name="gmail_suppressions")
    op.drop_index(op.f("ix_gmail_suppressions_sender_domain"), table_name="gmail_suppressions")
    op.drop_index(op.f("ix_gmail_suppressions_source_id"), table_name="gmail_suppressions")
    op.drop_index(op.f("ix_gmail_suppressions_scope"), table_name="gmail_suppressions")
    op.drop_index(op.f("ix_gmail_suppressions_user_id"), table_name="gmail_suppressions")
    op.drop_index(op.f("ix_gmail_suppressions_id"), table_name="gmail_suppressions")
    op.drop_table("gmail_suppressions")
