from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.job import Job, ProviderSyncLog, QuotaUsage
from app.providers.registry import list_enabled_provider_names, list_provider_statuses

SAMPLE_LIMIT = 8


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _trim_text(value: str | None, limit: int = 280) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def _serialize_job_sample(job: Job) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "provider": job.provider,
        "provider_job_id": str(job.provider_job_id),
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "is_active": bool(job.is_active),
        "is_remote": bool(job.is_remote),
        "display_tier": job.display_tier,
        "staleness_status": job.staleness_status,
        "provider_url_status": job.provider_url_status,
        "apply_url_status": job.apply_url_status,
        "repost_count": int(job.repost_count or 0),
        "dedup_hash": job.dedup_hash,
        "published_at": _iso(job.published_at),
        "first_seen_at": _iso(job.first_seen_at),
        "last_seen_at": _iso(job.last_seen_at),
        "source_tags": list(job.source_tags or [])[:6],
    }


def _serialize_sync_log(entry: ProviderSyncLog) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "provider": entry.provider,
        "category": entry.category,
        "started_at": _iso(entry.started_at),
        "completed_at": _iso(entry.completed_at),
        "pages_fetched": int(entry.pages_fetched or 0),
        "jobs_found": int(entry.jobs_found or 0),
        "jobs_new": int(entry.jobs_new or 0),
        "jobs_updated": int(entry.jobs_updated or 0),
        "jobs_deduplicated": int(entry.jobs_deduplicated or 0),
        "requests_used": int(entry.requests_used or 0),
        "stopped_reason": entry.stopped_reason,
        "error_message": _trim_text(entry.error_message, 220) or None,
    }


def _serialize_quota_row(entry: QuotaUsage) -> dict[str, Any]:
    return {
        "provider": entry.provider,
        "hour_bucket": _iso(entry.hour_bucket),
        "request_count": int(entry.request_count or 0),
    }


def _count_jobs(db: Session, *criteria) -> int:
    query = db.query(func.count(Job.id))
    if criteria:
        query = query.filter(*criteria)
    return int(query.scalar() or 0)


def _group_counts(db: Session, column, *criteria) -> list[dict[str, Any]]:
    query = db.query(column, func.count(Job.id))
    if criteria:
        query = query.filter(*criteria)
    rows = query.group_by(column).order_by(func.count(Job.id).desc(), column.asc()).all()
    return [{"value": value or "unknown", "count": int(count or 0)} for value, count in rows]


def _active_dedup_collisions(db: Session) -> list[dict[str, Any]]:
    rows = (
        db.query(Job.dedup_hash, func.count(Job.id))
        .filter(Job.is_active.is_(True), Job.dedup_hash.is_not(None))
        .group_by(Job.dedup_hash)
        .having(func.count(Job.id) > 1)
        .order_by(func.count(Job.id).desc(), Job.dedup_hash.asc())
        .all()
    )
    return [{"dedup_hash": dedup_hash, "count": int(count or 0)} for dedup_hash, count in rows]


def _job_health_summary(db: Session) -> dict[str, Any]:
    active_jobs = _count_jobs(db, Job.is_active.is_(True))
    inactive_jobs = _count_jobs(db, Job.is_active.is_(False))
    bad_provider_urls = _count_jobs(db, Job.provider_url_status == "bad")
    bad_apply_urls = _count_jobs(db, Job.apply_url_status == "bad")
    stale_jobs = _count_jobs(db, Job.staleness_status != "fresh")
    hashed_active_jobs = _count_jobs(db, Job.is_active.is_(True), Job.dedup_hash.is_not(None))
    null_hash_active_jobs = _count_jobs(db, Job.is_active.is_(True), Job.dedup_hash.is_(None))
    collisions = _active_dedup_collisions(db)

    return {
        "counts": {
            "total_jobs": active_jobs + inactive_jobs,
            "active_jobs": active_jobs,
            "inactive_jobs": inactive_jobs,
            "bad_provider_urls": bad_provider_urls,
            "bad_apply_urls": bad_apply_urls,
            "stale_jobs": stale_jobs,
            "active_hashed_jobs": hashed_active_jobs,
            "active_null_hash_jobs": null_hash_active_jobs,
        },
        "by_provider": _group_counts(db, Job.provider),
        "by_display_tier": _group_counts(db, Job.display_tier),
        "by_staleness_status": _group_counts(db, Job.staleness_status),
        "by_provider_url_status": _group_counts(db, Job.provider_url_status),
        "by_apply_url_status": _group_counts(db, Job.apply_url_status),
        "dedup": {
            "active_collision_count": len(collisions),
            "collision_samples": collisions[:SAMPLE_LIMIT],
        },
    }


def build_job_board_overview(db: Session) -> dict[str, Any]:
    provider_statuses = list_provider_statuses()
    latest_syncs = (
        db.query(ProviderSyncLog)
        .order_by(ProviderSyncLog.started_at.desc())
        .limit(10)
        .all()
    )
    recent_quota = (
        db.query(QuotaUsage)
        .order_by(QuotaUsage.hour_bucket.desc(), QuotaUsage.request_count.desc(), QuotaUsage.provider.asc())
        .limit(12)
        .all()
    )
    health = _job_health_summary(db)

    return {
        "providers": {
            "statuses": provider_statuses,
            "display_enabled": list_enabled_provider_names(control_name="display"),
            "ingest_enabled": list_enabled_provider_names(control_name="ingest"),
            "scheduled_enabled": list_enabled_provider_names(control_name="scheduled"),
        },
        "recent_syncs": [_serialize_sync_log(entry) for entry in latest_syncs],
        "quota_usage": [_serialize_quota_row(entry) for entry in recent_quota],
        "database": health,
    }


def build_job_board_db_insights(db: Session) -> dict[str, Any]:
    recent_inserts = (
        db.query(Job)
        .order_by(Job.first_seen_at.desc().nullslast(), Job.id.desc())
        .limit(SAMPLE_LIMIT)
        .all()
    )
    recent_updates = (
        db.query(Job)
        .order_by(Job.last_seen_at.desc().nullslast(), Job.id.desc())
        .limit(SAMPLE_LIMIT)
        .all()
    )
    bad_provider_urls = (
        db.query(Job)
        .filter(Job.provider_url_status == "bad")
        .order_by(Job.last_seen_at.desc().nullslast(), Job.id.desc())
        .limit(SAMPLE_LIMIT)
        .all()
    )
    bad_apply_urls = (
        db.query(Job)
        .filter(Job.apply_url_status == "bad")
        .order_by(Job.last_seen_at.desc().nullslast(), Job.id.desc())
        .limit(SAMPLE_LIMIT)
        .all()
    )
    stale_jobs = (
        db.query(Job)
        .filter(Job.staleness_status != "fresh")
        .order_by(Job.last_seen_at.desc().nullslast(), Job.id.desc())
        .limit(SAMPLE_LIMIT)
        .all()
    )
    dedup_owners = (
        db.query(Job)
        .filter(Job.is_active.is_(True), Job.dedup_hash.is_not(None))
        .order_by(Job.repost_count.desc(), Job.last_seen_at.desc().nullslast(), Job.id.desc())
        .limit(SAMPLE_LIMIT)
        .all()
    )
    recent_syncs = (
        db.query(ProviderSyncLog)
        .order_by(ProviderSyncLog.started_at.desc())
        .limit(SAMPLE_LIMIT)
        .all()
    )
    health = _job_health_summary(db)

    return {
        "summary": health["counts"],
        "dedup": health["dedup"],
        "recent_syncs": [_serialize_sync_log(entry) for entry in recent_syncs],
        "recent_inserts": [_serialize_job_sample(job) for job in recent_inserts],
        "recent_updates": [_serialize_job_sample(job) for job in recent_updates],
        "bad_provider_urls": [_serialize_job_sample(job) for job in bad_provider_urls],
        "bad_apply_urls": [_serialize_job_sample(job) for job in bad_apply_urls],
        "stale_jobs": [_serialize_job_sample(job) for job in stale_jobs],
        "dedup_owners": [_serialize_job_sample(job) for job in dedup_owners],
    }


def build_compact_job_board_service_status(db: Session) -> dict[str, Any]:
    health = _job_health_summary(db)
    collision_count = int(health["dedup"]["active_collision_count"] or 0)
    bad_provider_urls = int(health["counts"]["bad_provider_urls"] or 0)
    status = "healthy"
    if collision_count > 0:
        status = "unhealthy"
    elif bad_provider_urls > 0:
        status = "degraded"

    latest_sync = (
        db.query(ProviderSyncLog)
        .order_by(ProviderSyncLog.started_at.desc())
        .limit(1)
        .first()
    )

    return {
        "status": status,
        "counts": health["counts"],
        "dedup": {
            "active_collision_count": collision_count,
        },
        "display_enabled_providers": list_enabled_provider_names(control_name="display"),
        "latest_sync": _serialize_sync_log(latest_sync) if latest_sync else None,
    }
