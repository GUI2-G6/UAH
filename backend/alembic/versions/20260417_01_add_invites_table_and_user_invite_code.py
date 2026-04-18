"""add invites table and user invite_code_used column

Revision ID: 20260417_01
Revises: 20260415_02
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260417_01"
down_revision = "20260415_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "invites" not in existing_tables:
        op.create_table(
            "invites",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("used_by", sa.Integer(), nullable=True),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.ForeignKeyConstraint(["used_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_invites_code", "invites", ["code"], unique=True)

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "invite_code_used" not in user_columns:
        op.add_column("users", sa.Column("invite_code_used", sa.String(length=64), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "users" in existing_tables:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "invite_code_used" in user_columns:
            op.drop_column("users", "invite_code_used")

    if "invites" in existing_tables:
        invite_indexes = {index["name"] for index in inspector.get_indexes("invites")}
        if "ix_invites_code" in invite_indexes:
            op.drop_index("ix_invites_code", table_name="invites")
        op.drop_table("invites")
