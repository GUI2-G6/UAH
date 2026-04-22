"""add beta access requests table

Revision ID: 20260422_01
Revises: 20260417_03
Create Date: 2026-04-22
"""

from alembic import op
import sqlalchemy as sa


revision = "20260422_01"
down_revision = "20260417_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "beta_access_requests" not in existing_tables:
        op.create_table(
            "beta_access_requests",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("full_name", sa.String(length=120), nullable=True),
            sa.Column("source_surface", sa.String(length=64), nullable=True),
            sa.Column("notes", sa.String(length=1200), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )

    indexes = {index["name"] for index in inspector.get_indexes("beta_access_requests")}
    if "ix_beta_access_requests_email" not in indexes:
        op.create_index("ix_beta_access_requests_email", "beta_access_requests", ["email"], unique=False)
    if "ix_beta_access_requests_created_at" not in indexes:
        op.create_index("ix_beta_access_requests_created_at", "beta_access_requests", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "beta_access_requests" not in existing_tables:
        return

    indexes = {index["name"] for index in inspector.get_indexes("beta_access_requests")}
    if "ix_beta_access_requests_created_at" in indexes:
        op.drop_index("ix_beta_access_requests_created_at", table_name="beta_access_requests")
    if "ix_beta_access_requests_email" in indexes:
        op.drop_index("ix_beta_access_requests_email", table_name="beta_access_requests")

    op.drop_table("beta_access_requests")
