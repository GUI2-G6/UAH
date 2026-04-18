"""extend invites for multi-use and labels

Revision ID: 20260417_03
Revises: 20260417_02
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260417_03"
down_revision = "20260417_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "invites" not in existing_tables:
        return

    invite_columns = {column["name"] for column in inspector.get_columns("invites")}

    if "name" not in invite_columns:
        op.add_column("invites", sa.Column("name", sa.String(length=120), nullable=True))

    if "max_uses" not in invite_columns:
        op.add_column(
            "invites",
            sa.Column("max_uses", sa.Integer(), nullable=False, server_default=sa.text("1")),
        )

    if "use_count" not in invite_columns:
        op.add_column(
            "invites",
            sa.Column("use_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        )

    op.execute("UPDATE invites SET max_uses = COALESCE(max_uses, 1)")
    op.execute(
        "UPDATE invites SET use_count = CASE "
        "WHEN used_by IS NULL THEN COALESCE(use_count, 0) "
        "WHEN COALESCE(use_count, 0) < 1 THEN 1 "
        "ELSE use_count END"
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "invites" not in existing_tables:
        return

    invite_columns = {column["name"] for column in inspector.get_columns("invites")}

    if "use_count" in invite_columns:
        op.drop_column("invites", "use_count")

    if "max_uses" in invite_columns:
        op.drop_column("invites", "max_uses")

    if "name" in invite_columns:
        op.drop_column("invites", "name")
