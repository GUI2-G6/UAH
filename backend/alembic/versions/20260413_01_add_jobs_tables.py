"""add jobs catalog tables

Revision ID: 20260413_01
Revises:
Create Date: 2026-04-13 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260413_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_job_id", sa.String(length=255), nullable=False),
        sa.Column("provider_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("company_url", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("is_remote", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("job_type", sa.String(length=50), nullable=True),
        sa.Column("experience_level", sa.String(length=50), nullable=True),
        sa.Column("categories", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("quality_flags", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("consecutive_misses", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("display_tier", sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_job_id", name="uq_jobs_provider_provider_job_id"),
    )
    op.create_index(
        "ix_jobs_display_tier_remote_experience_active",
        "jobs",
        ["display_tier", "is_remote", "experience_level", "is_active"],
        unique=False,
    )
    op.create_index("ix_jobs_last_seen_at", "jobs", ["last_seen_at"], unique=False)
    op.create_index("ix_jobs_provider_provider_job_id", "jobs", ["provider", "provider_job_id"], unique=False)
    op.create_index("ix_jobs_company", "jobs", ["company"], unique=False)
    op.create_index("ix_jobs_categories_gin", "jobs", ["categories"], unique=False, postgresql_using="gin")

    op.create_table(
        "provider_sync_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pages_fetched", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("jobs_found", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("jobs_new", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("jobs_updated", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("requests_used", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("stopped_reason", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_sync_log_provider", "provider_sync_log", ["provider"], unique=False)
    op.create_index("ix_provider_sync_log_category", "provider_sync_log", ["category"], unique=False)

    op.create_table(
        "quota_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("hour_bucket", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "hour_bucket", name="uq_quota_usage_provider_hour_bucket"),
    )
    op.create_index("ix_quota_usage_provider", "quota_usage", ["provider"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quota_usage_provider", table_name="quota_usage")
    op.drop_table("quota_usage")
    op.drop_index("ix_provider_sync_log_category", table_name="provider_sync_log")
    op.drop_index("ix_provider_sync_log_provider", table_name="provider_sync_log")
    op.drop_table("provider_sync_log")
    op.drop_index("ix_jobs_categories_gin", table_name="jobs", postgresql_using="gin")
    op.drop_index("ix_jobs_company", table_name="jobs")
    op.drop_index("ix_jobs_provider_provider_job_id", table_name="jobs")
    op.drop_index("ix_jobs_last_seen_at", table_name="jobs")
    op.drop_index("ix_jobs_display_tier_remote_experience_active", table_name="jobs")
    op.drop_table("jobs")
