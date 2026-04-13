"""add job health, provenance, and staleness fields

Revision ID: 20260413_02
Revises: 20260413_01
Create Date: 2026-04-13 00:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260413_02"
down_revision = "20260413_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("provider_url_status", sa.String(length=20), nullable=False, server_default=sa.text("'unknown'")))
    op.add_column("jobs", sa.Column("provider_url_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("provider_url_error", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("apply_url", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("apply_host", sa.String(length=255), nullable=True))
    op.add_column("jobs", sa.Column("apply_portal", sa.String(length=50), nullable=False, server_default=sa.text("'missing'")))
    op.add_column("jobs", sa.Column("apply_url_status", sa.String(length=20), nullable=False, server_default=sa.text("'missing'")))
    op.add_column("jobs", sa.Column("apply_url_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("apply_url_error", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("source_tags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("jobs", sa.Column("first_published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("content_fingerprint", sa.String(length=64), nullable=True))
    op.add_column("jobs", sa.Column("last_content_change_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("staleness_status", sa.String(length=30), nullable=False, server_default=sa.text("'fresh'")))
    op.add_column("jobs", sa.Column("staleness_flags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("jobs", sa.Column("staleness_checked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("jobs", sa.Column("repost_count", sa.Integer(), nullable=False, server_default=sa.text("0")))

    op.execute("UPDATE jobs SET first_published_at = published_at WHERE first_published_at IS NULL")

    op.create_index("ix_jobs_provider_url_status", "jobs", ["provider_url_status"], unique=False)
    op.create_index("ix_jobs_staleness_status", "jobs", ["staleness_status"], unique=False)
    op.create_index("ix_jobs_first_published_at", "jobs", ["first_published_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_jobs_first_published_at", table_name="jobs")
    op.drop_index("ix_jobs_staleness_status", table_name="jobs")
    op.drop_index("ix_jobs_provider_url_status", table_name="jobs")

    op.drop_column("jobs", "repost_count")
    op.drop_column("jobs", "staleness_checked_at")
    op.drop_column("jobs", "staleness_flags")
    op.drop_column("jobs", "staleness_status")
    op.drop_column("jobs", "last_content_change_at")
    op.drop_column("jobs", "content_fingerprint")
    op.drop_column("jobs", "first_published_at")
    op.drop_column("jobs", "source_tags")
    op.drop_column("jobs", "apply_url_error")
    op.drop_column("jobs", "apply_url_checked_at")
    op.drop_column("jobs", "apply_url_status")
    op.drop_column("jobs", "apply_portal")
    op.drop_column("jobs", "apply_host")
    op.drop_column("jobs", "apply_url")
    op.drop_column("jobs", "provider_url_error")
    op.drop_column("jobs", "provider_url_checked_at")
    op.drop_column("jobs", "provider_url_status")
