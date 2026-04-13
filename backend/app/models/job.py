import uuid

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.sql import func

from app.db.base import Base


class Job(Base):
    """Locally cached job posting normalized from one or more providers."""

    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("provider", "provider_job_id", name="uq_jobs_provider_provider_job_id"),
        Index(
            "ix_jobs_display_tier_remote_experience_active",
            "display_tier",
            "is_remote",
            "experience_level",
            "is_active",
        ),
        Index("ix_jobs_categories_gin", "categories", postgresql_using="gin"),
        Index("ix_jobs_last_seen_at", "last_seen_at"),
        Index("ix_jobs_provider_provider_job_id", "provider", "provider_job_id"),
        Index("ix_jobs_company", "company"),
        Index("ix_jobs_provider_url_status", "provider_url_status"),
        Index("ix_jobs_staleness_status", "staleness_status"),
        Index("ix_jobs_first_published_at", "first_published_at"),
        Index(
            "idx_jobs_dedup_hash",
            "dedup_hash",
            unique=True,
            postgresql_where=text("dedup_hash IS NOT NULL AND is_active = true"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False)
    provider_job_id = Column(String(255), nullable=False)
    provider_url = Column(Text, nullable=True)
    provider_url_status = Column(String(20), nullable=False, default="unknown")
    provider_url_checked_at = Column(DateTime(timezone=True), nullable=True)
    provider_url_error = Column(Text, nullable=True)
    apply_url = Column(Text, nullable=True)
    apply_host = Column(String(255), nullable=True)
    apply_portal = Column(String(50), nullable=False, default="missing")
    apply_url_status = Column(String(20), nullable=False, default="missing")
    apply_url_checked_at = Column(DateTime(timezone=True), nullable=True)
    apply_url_error = Column(Text, nullable=True)
    source_tags = Column(ARRAY(Text), nullable=False, default=list)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    company_url = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    is_remote = Column(Boolean, nullable=False, default=False)
    job_type = Column(String(50), nullable=True)
    experience_level = Column(String(50), nullable=True)
    categories = Column(ARRAY(Text), nullable=False, default=list)
    description = Column(Text, nullable=True)
    short_description = Column(Text, nullable=True)
    quality_score = Column(Float, nullable=False, default=0.0)
    quality_flags = Column(ARRAY(Text), nullable=False, default=list)
    consecutive_misses = Column(Integer, nullable=False, default=0)
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    first_published_at = Column(DateTime(timezone=True), nullable=True)
    content_fingerprint = Column(String(64), nullable=True)
    last_content_change_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_featured = Column(Boolean, nullable=False, default=False)
    display_tier = Column(String(20), nullable=False, default="active")
    staleness_status = Column(String(30), nullable=False, default="fresh")
    staleness_flags = Column(ARRAY(Text), nullable=False, default=list)
    staleness_checked_at = Column(DateTime(timezone=True), nullable=True)
    repost_count = Column(Integer, nullable=False, default=0)
    dedup_hash = Column(String(32), nullable=True)


class ProviderSyncLog(Base):
    """Operational log for background provider/category sweeps."""

    __tablename__ = "provider_sync_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False, index=True)
    category = Column(String(255), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    pages_fetched = Column(Integer, nullable=False, default=0)
    jobs_found = Column(Integer, nullable=False, default=0)
    jobs_new = Column(Integer, nullable=False, default=0)
    jobs_updated = Column(Integer, nullable=False, default=0)
    jobs_deduplicated = Column(Integer, nullable=False, default=0)
    requests_used = Column(Integer, nullable=False, default=0)
    stopped_reason = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)


class QuotaUsage(Base):
    """Hourly outbound provider request accounting."""

    __tablename__ = "quota_usage"
    __table_args__ = (
        UniqueConstraint("provider", "hour_bucket", name="uq_quota_usage_provider_hour_bucket"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False, index=True)
    hour_bucket = Column(DateTime(timezone=True), nullable=False)
    request_count = Column(Integer, nullable=False, default=0)
