from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import logging
import time

import redis

from app.core.config import settings
from app.db.session import session_scope
from app.models.job import Job, ProviderSyncLog, QuotaUsage
from app.providers.registry import get_adapter
from app.services.ingest import mark_unseen_jobs, run_cleanup, upsert_job
from app.services.provider_requests import ProviderQuotaExceeded
from app.worker import celery_app

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def _lock_key(provider: str, category: str) -> str:
    return f"uah:job_sync:lock:{provider}:{category}"


def _cleanup_lock_key() -> str:
    return "uah:job_sync:cleanup_lock"


def _get_redis_client() -> redis.Redis | None:
    global _redis_client
    try:
        if _redis_client is None:
            _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except redis.RedisError:
        _redis_client = None
        return None


def _acquire_lock(key: str, ttl_seconds: int) -> bool:
    client = _get_redis_client()
    if client is None:
        return True
    return bool(client.set(key, datetime.now(timezone.utc).isoformat(), ex=max(ttl_seconds, 60), nx=True))


def _release_lock(key: str) -> None:
    client = _get_redis_client()
    if client is None:
        return
    try:
        client.delete(key)
    except redis.RedisError:
        logger.debug("Failed to release Redis lock %s", key)


def _lock_exists(provider: str, category: str) -> bool:
    client = _get_redis_client()
    if client is None:
        return False
    try:
        return bool(client.exists(_lock_key(provider, category)))
    except redis.RedisError:
        return False


def _category_sort_key(item: tuple[str, dict[str, int]]) -> tuple[int, str]:
    category, config = item
    return (int(config.get("priority", 100)), category)


def confirm_quota(provider: str, db_session=None) -> bool:
    """Return True when the provider is still below the soft hourly quota threshold."""
    adapter = get_adapter(provider)
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        bucket = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        row = (
            db.query(QuotaUsage)
            .filter(QuotaUsage.provider == provider, QuotaUsage.hour_bucket == bucket)
            .first()
        )
        if row is None:
            return True
        threshold = max(int(adapter.rate_limit_per_hour * 0.8), 1)
        return int(row.request_count or 0) < threshold


def _compute_fresh_ratio(provider: str, jobs: list, db_session=None) -> float:
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        provider_job_ids = [job.provider_job_id for job in jobs if job.provider_job_id]
        if not provider_job_ids:
            return 0.0
        fresh_cutoff = datetime.now(timezone.utc) - timedelta(hours=max(int(settings.JOB_SYNC_STALE_THRESHOLD_HOURS), 1))
        fresh_matches = (
            db.query(Job)
            .filter(
                Job.provider == provider,
                Job.provider_job_id.in_(provider_job_ids),
                Job.consecutive_misses == 0,
                Job.last_seen_at >= fresh_cutoff,
            )
            .count()
        )
        return fresh_matches / len(provider_job_ids)


def _sync_anchor(row: ProviderSyncLog | None) -> datetime | None:
    if row is None:
        return None
    return row.completed_at or row.started_at


@celery_app.task(
    bind=True,
    name="app.tasks.job_sync.sweep_category",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def sweep_category(self, provider: str, category: str):
    """Fetch one provider/category slice, upsert rows, and expire unseen jobs."""
    lock_key = _lock_key(provider, category)
    if not _acquire_lock(lock_key, int(settings.JOB_SYNC_LOCK_TTL_SECONDS)):
        return {"status": "skipped_locked", "provider": provider, "category": category}

    log_id = None
    try:
        adapter = get_adapter(provider)
        with session_scope() as db:
            log_row = ProviderSyncLog(provider=provider, category=category, started_at=datetime.now(timezone.utc))
            db.add(log_row)
            db.commit()
            db.refresh(log_row)
            log_id = log_row.id

        seen_ids: set[str] = set()
        pages_fetched = 0
        jobs_found = 0
        jobs_new = 0
        jobs_updated = 0
        requests_used = 0
        stop_reason = "no_more_pages"
        page = 0
        min_interval = 3600 / max(adapter.rate_limit_per_hour, 1)

        while True:
            if not confirm_quota(provider):
                stop_reason = "quota_threshold_hit"
                break

            jobs = adapter.fetch({"category": [category], "page": page})
            requests_used += 1
            pages_fetched += 1

            if not jobs:
                stop_reason = "no_more_pages"
                break

            jobs_found += len(jobs)
            fresh_ratio = _compute_fresh_ratio(provider, jobs)

            with session_scope() as db:
                for job in jobs:
                    seen_ids.add(job.provider_job_id)
                    state, _ = upsert_job(job, db_session=db)
                    if state == "inserted":
                        jobs_new += 1
                    elif state == "updated":
                        jobs_updated += 1

            if fresh_ratio >= 0.80:
                stop_reason = "threshold_hit"
                break

            if len(jobs) < adapter.max_page_size:
                stop_reason = "no_more_pages"
                break

            page += 1
            if min_interval > 0:
                time.sleep(min(min_interval, 10.0))

        mark_unseen_jobs(provider=provider, category=category, seen_ids=seen_ids)

        with session_scope() as db:
            log_row = db.query(ProviderSyncLog).filter(ProviderSyncLog.id == log_id).first()
            if log_row is not None:
                log_row.completed_at = datetime.now(timezone.utc)
                log_row.pages_fetched = pages_fetched
                log_row.jobs_found = jobs_found
                log_row.jobs_new = jobs_new
                log_row.jobs_updated = jobs_updated
                log_row.requests_used = requests_used
                log_row.stopped_reason = stop_reason
                db.commit()

        return {
            "status": "completed",
            "provider": provider,
            "category": category,
            "pages_fetched": pages_fetched,
            "jobs_found": jobs_found,
            "jobs_new": jobs_new,
            "jobs_updated": jobs_updated,
            "requests_used": requests_used,
            "stopped_reason": stop_reason,
        }
    except ProviderQuotaExceeded:
        with session_scope() as db:
            if log_id is not None:
                log_row = db.query(ProviderSyncLog).filter(ProviderSyncLog.id == log_id).first()
                if log_row is not None:
                    log_row.completed_at = datetime.now(timezone.utc)
                    log_row.stopped_reason = "quota_threshold_hit"
                    db.commit()
        return {"status": "quota_threshold_hit", "provider": provider, "category": category}
    except Exception as exc:
        with session_scope() as db:
            if log_id is not None:
                log_row = db.query(ProviderSyncLog).filter(ProviderSyncLog.id == log_id).first()
                if log_row is not None:
                    log_row.completed_at = datetime.now(timezone.utc)
                    log_row.stopped_reason = "error"
                    log_row.error_message = str(exc)
                    db.commit()
        raise
    finally:
        _release_lock(lock_key)


@celery_app.task(
    bind=True,
    name="app.tasks.job_sync.dispatch_scheduled_sweeps",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def dispatch_scheduled_sweeps(self):
    """Queue sweeps for provider/category pairs that are currently due."""
    if not settings.JOB_SYNC_ENABLED:
        return {"queued": []}

    queued: list[dict[str, str]] = []
    now = datetime.now(timezone.utc)
    schedule = settings.JOB_SYNC_CATEGORY_SCHEDULE

    with session_scope() as db:
        # TODO: If UAH adds provider-specific schedules or enablement rules, branch that logic here.
        for provider in settings.JOB_SYNC_ENABLED_PROVIDERS:
            for category, config in sorted(schedule.items(), key=_category_sort_key):
                if _lock_exists(provider, category):
                    continue

                latest = (
                    db.query(ProviderSyncLog)
                    .filter(ProviderSyncLog.provider == provider, ProviderSyncLog.category == category)
                    .order_by(ProviderSyncLog.started_at.desc())
                    .first()
                )
                anchor = _sync_anchor(latest)
                interval_minutes = max(int(config.get("interval_minutes", 60)), 5)
                if anchor is not None and (now - anchor) < timedelta(minutes=interval_minutes):
                    continue

                sweep_category.delay(provider=provider, category=category)
                queued.append({"provider": provider, "category": category})

    return {"queued": queued}


@celery_app.task(
    bind=True,
    name="app.tasks.job_sync.cleanup_cached_jobs",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def cleanup_cached_jobs(self):
    """Delete stale hidden jobs on a slower cadence than provider sweeps."""
    lock_key = _cleanup_lock_key()
    if not _acquire_lock(lock_key, int(settings.JOB_SYNC_CLEANUP_LOCK_TTL_SECONDS)):
        return {"status": "skipped_locked"}
    try:
        deleted = run_cleanup()
        return {"status": "completed", "deleted": deleted}
    finally:
        _release_lock(lock_key)
