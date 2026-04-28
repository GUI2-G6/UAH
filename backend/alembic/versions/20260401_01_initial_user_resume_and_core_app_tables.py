"""Initial core app tables (users, resumes, saved_jobs, etc.)

Revision ID: 20260401_01
Revises: None
Create Date: 2026-04-01

The jobs-catalog migrations (20260413_*) and resume markdown metadata (20260415_01) assumed these
tables already existed from older workflows. This revision brings fresh databases in line.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260401_01"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return name in set(insp.get_table_names())


def upgrade() -> None:
    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False, unique=True),
            sa.Column("username", sa.String(length=100), nullable=False, unique=True),
            sa.Column("hashed_password", sa.String(length=255), nullable=True),
            sa.Column("first_name", sa.String(length=100), nullable=True),
            sa.Column("last_name", sa.String(length=100), nullable=True),
            sa.Column("is_admin", sa.Boolean(), nullable=True, server_default=sa.text("false")),
            sa.Column("is_developer", sa.Boolean(), nullable=True, server_default=sa.text("false")),
            sa.Column("linkedIn_id", sa.String(length=255), nullable=True, unique=True),
            sa.Column("google_id", sa.String(length=255), nullable=True, unique=True),
            sa.Column("full_name", sa.String(length=255), nullable=True),
            sa.Column("picture_url", sa.String(length=255), nullable=True),
            sa.Column("gmail_refresh_token", sa.Text(), nullable=True),
            sa.Column("gmail_email", sa.String(length=255), nullable=True),
            sa.Column("password_reset_token_id", sa.String(length=255), nullable=True),
            sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("email_verify_token_id", sa.String(length=255), nullable=True),
            sa.Column("email_verify_target_email", sa.String(length=255), nullable=True),
            sa.Column("email_verify_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("email_verified", sa.Boolean(), nullable=True, server_default=sa.text("false")),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        )
    if not _has_table("applicant_profiles"):
        op.create_table(
            "applicant_profiles",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False, server_default=sa.text("'Default'")),
            sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
            sa.Column("first_name", sa.String(length=100), nullable=True),
            sa.Column("last_name", sa.String(length=100), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("phone", sa.String(length=50), nullable=True),
            sa.Column("linkedin", sa.String(length=255), nullable=True),
            sa.Column("portfolio", sa.String(length=255), nullable=True),
            sa.Column("street_address", sa.String(length=255), nullable=True),
            sa.Column("city", sa.String(length=100), nullable=True),
            sa.Column("state", sa.String(length=50), nullable=True),
            sa.Column("zip", sa.String(length=20), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("work_auth", sa.String(length=100), nullable=True),
            sa.Column("requires_sponsorship", sa.String(length=50), nullable=True),
            sa.Column("degree", sa.String(length=100), nullable=True),
            sa.Column("major", sa.String(length=100), nullable=True),
            sa.Column("university", sa.String(length=200), nullable=True),
            sa.Column("grad_year", sa.String(length=10), nullable=True),
            sa.Column("gpa", sa.String(length=20), nullable=True),
            sa.Column("years_experience", sa.String(length=20), nullable=True),
            sa.Column("job_title", sa.String(length=150), nullable=True),
            sa.Column("skills_text", sa.Text(), nullable=True),
            sa.Column("certifications_text", sa.Text(), nullable=True),
            sa.Column("professional_links_text", sa.Text(), nullable=True),
            sa.Column("education_history_text", sa.Text(), nullable=True),
            sa.Column("employment_history_text", sa.Text(), nullable=True),
            sa.Column("canonical_data", postgresql.JSONB(), nullable=True),
            sa.Column("token_map", postgresql.JSONB(), nullable=True),
            sa.Column("demographic_gender", sa.String(length=50), nullable=True),
            sa.Column("demographic_ethnicity", sa.String(length=100), nullable=True),
            sa.Column("veteran_status", sa.String(length=200), nullable=True),
            sa.Column("disability_status", sa.String(length=200), nullable=True),
            sa.Column("california_resident", sa.String(length=100), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_applicant_profiles_user_id", "applicant_profiles", ["user_id"], unique=False)

    if not _has_table("resumes"):
        # Columns match app.models.Resume except raw_markdown_{source,method,updated_at} (added in 20260415_01)
        op.create_table(
            "resumes",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("file_name", sa.String(length=255), nullable=False),
            sa.Column("pdf_data", postgresql.BYTEA(), nullable=True),
            sa.Column("raw_markdown", sa.Text(), nullable=True),
            sa.Column("structured_data", postgresql.JSONB(), nullable=True),
            sa.Column("portal_ready", sa.Boolean(), nullable=True, server_default=sa.text("false")),
            sa.Column("parse_method", sa.String(length=50), nullable=True),
            sa.Column("review_status", sa.String(length=50), nullable=True),
            sa.Column("review_draft", postgresql.JSONB(), nullable=True),
            sa.Column("review_updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_resumes_user_id", "resumes", ["user_id"], unique=False)

    if not _has_table("saved_jobs"):
        # State before 20260415_02: job_id NOT NULL, url VARCHAR(255) NOT NULL
        op.create_table(
            "saved_jobs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=50), nullable=True),
            sa.Column("provider_job_id", sa.String(length=255), nullable=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("company", sa.String(length=255), nullable=False),
            sa.Column("url", sa.String(length=255), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_saved_jobs_user_id", "saved_jobs", ["user_id"], unique=False)
        op.create_index("ix_saved_jobs_job_id", "saved_jobs", ["job_id"], unique=False)
        op.create_index("ix_saved_jobs_provider", "saved_jobs", ["provider"], unique=False)
        op.create_index("ix_saved_jobs_provider_job_id", "saved_jobs", ["provider_job_id"], unique=False)
        op.create_index("ix_saved_jobs_created_at", "saved_jobs", ["created_at"], unique=False)

    if not _has_table("muse_supported_locations"):
        op.create_table(
            "muse_supported_locations",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("location_name", sa.String(length=255), nullable=False),
            sa.Column("normalized_key", sa.String(length=255), nullable=False),
            sa.Column("country_code", sa.String(length=2), nullable=False),
            sa.Column("country_name", sa.String(length=120), nullable=True),
            sa.Column("observed_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.UniqueConstraint("normalized_key", name="uq_muse_supported_locations_normalized_key"),
        )
        op.create_index("ix_muse_supported_locations_normalized_key", "muse_supported_locations", ["normalized_key"], unique=False)
        op.create_index("ix_muse_supported_locations_country_code", "muse_supported_locations", ["country_code"], unique=False)

    if not _has_table("parse_jobs"):
        op.create_table(
            "parse_jobs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("resume_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("method", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="queued"),
            sa.Column("progress_stage", sa.String(length=100), nullable=True),
            sa.Column("error_code", sa.String(length=100), nullable=True),
            sa.Column("error_message", sa.String(length=500), nullable=True),
            sa.Column("result_summary", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_parse_jobs_resume_id", "parse_jobs", ["resume_id"], unique=False)
        op.create_index("ix_parse_jobs_user_id", "parse_jobs", ["user_id"], unique=False)

    if not _has_table("apply_sessions"):
        op.create_table(
            "apply_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("job_id", sa.String(length=255), nullable=True),
            sa.Column("job_title", sa.String(length=255), nullable=False),
            sa.Column("company", sa.String(length=255), nullable=False),
            sa.Column("ats_url", sa.String(length=1024), nullable=True),
            sa.Column("job_url", sa.String(length=1024), nullable=True),
            sa.Column("status", sa.String(length=50), nullable=True, server_default="started"),
            sa.Column("platform", sa.String(length=100), nullable=True),
            sa.Column("resume_id", sa.Integer(), nullable=True),
            sa.Column("fields_matched", sa.Integer(), nullable=True),
            sa.Column("fields_filled", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_apply_sessions_user_id", "apply_sessions", ["user_id"], unique=False)

    if not _has_table("apply_session_events"):
        op.create_table(
            "apply_session_events",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=100), nullable=False),
            sa.Column("payload", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
            sa.ForeignKeyConstraint(["session_id"], ["apply_sessions.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_apply_session_events_session_id", "apply_session_events", ["session_id"], unique=False)


def downgrade() -> None:
    if _has_table("apply_session_events"):
        op.drop_table("apply_session_events")
    if _has_table("apply_sessions"):
        op.drop_table("apply_sessions")
    if _has_table("parse_jobs"):
        op.drop_table("parse_jobs")
    if _has_table("muse_supported_locations"):
        op.drop_table("muse_supported_locations")
    if _has_table("saved_jobs"):
        op.drop_table("saved_jobs")
    if _has_table("resumes"):
        op.drop_table("resumes")
    if _has_table("applicant_profiles"):
        op.drop_table("applicant_profiles")
    if _has_table("users"):
        op.drop_table("users")
