"""add deleted identity tombstones table

Revision ID: 20260417_02
Revises: 20260417_01
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa


revision = "20260417_02"
down_revision = "20260417_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "deleted_identities" not in existing_tables:
        op.create_table(
            "deleted_identities",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("google_id", sa.String(length=255), nullable=True),
            sa.Column("deleted_user_id", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.CheckConstraint("email IS NOT NULL OR google_id IS NOT NULL", name="ck_deleted_identities_has_identity"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email", name="uq_deleted_identities_email"),
            sa.UniqueConstraint("google_id", name="uq_deleted_identities_google_id"),
        )
        op.create_index("ix_deleted_identities_email", "deleted_identities", ["email"], unique=False)
        op.create_index("ix_deleted_identities_google_id", "deleted_identities", ["google_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "deleted_identities" in existing_tables:
        indexes = {index["name"] for index in inspector.get_indexes("deleted_identities")}
        if "ix_deleted_identities_email" in indexes:
            op.drop_index("ix_deleted_identities_email", table_name="deleted_identities")
        if "ix_deleted_identities_google_id" in indexes:
            op.drop_index("ix_deleted_identities_google_id", table_name="deleted_identities")
        op.drop_table("deleted_identities")