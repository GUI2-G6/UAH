from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import logging
import time

import redis

from app.core.config import settings
from app.db.session import session_scope
from app.models.job import Job, ProviderSyncLog
from app.providers.registry import (
    get_adapter,
    get_provider_controls,
    get_provider_definition,
    list_enabled_provider_names,
    list_thin_sync_provider_names,
)
from app.services.ingest import (
    audit_stale_jobs_batch,
    backfill_job_health_batch,
    mark_unseen_jobs,
    run_cleanup,
    upsert_job,
)
from app.services.provider_requests import ProviderQuotaExceeded, confirm_request_budget
from app.worker import celery_app

logger = logging.getLogger(__name__)

JOOBLE_KEYWORDS = [
    "software engineer",
    "product manager",
    "data engineer",
    "devops",
    "designer",
]
JOOBLE_LOCATIONS = [
    "United States",
    "Remote",
    "New York",
    "San Francisco",
    "Boston",
    "Seattle",
    "Austin",
]

_redis_client: redis.Redis | None = None


def _lock_key(provider: str, category: str | None = None) -> str:
    suffix = (category or "__all__").strip().lower()
    return f"uah:job_sync:lock:{provider}:{suffix}"


def _cleanup_lock_key() -> str:
    return "uah:job_sync:cleanup_lock"


def _backfill_lock_key() -> str:
    return "uah:job_sync:link_backfill_lock"


def _stale_audit_lock_key() -> str:
    return "uah:job_sync:stale_audit_lock"


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


def _lock_exists(provider: str, category: str | None = None) -> bool:
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


def _sync_anchor(row: ProviderSyncLog | None) -> datetime | None:
    if row is None:
        return None
    return row.completed_at or row.started_at


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


def _page_start_for_provider(provider: str) -> int:
    if provider == "the_muse":
        return 0
    return 1


def _provider_sleep_seconds(provider: str) -> float:
    adapter = get_adapter(provider)
    return max(3600 / max(adapter.rate_limit_per_hour, 1), 0.0)


def confirm_quota(provider: str, db_session=None) -> bool:
    """Return True when the provider is still below its configured request budgets."""
    definition = get_provider_definition(provider)
    adapter = get_adapter(provider)
    return confirm_request_budget(
        provider_name=provider,
        rate_limit_per_hour=adapter.rate_limit_per_hour,
        daily_request_budget=definition.daily_request_budget,
        db_session=db_session,
    )


def _create_sync_log(provider: str, category: str | None = None):
    with session_scope() as db:
        log_row = ProviderSyncLog(
            provider=provider,
            category=category,
            started_at=datetime.now(timezone.utc),
        )
        db.add(log_row)
        db.commit()
        db.refresh(log_row)
        return log_row.id


def _finalize_sync_log(
    *,
    log_id: str | None,
    pages_fetched: int = 0,
    jobs_found: int = 0,
    jobs_new: int = 0,
    jobs_updated: int = 0,
    jobs_deduplicated: int = 0,
    requests_used: int = 0,
    stopped_reason: str | None = None,
    error_message: str | None = None,
) -> None:
    if log_id is None:
        return
    with session_scope() as db:
        log_row = db.query(ProviderSyncLog).filter(ProviderSyncLog.id == log_id).first()
        if log_row is None:
            return
        log_row.completed_at = datetime.now(timezone.utc)
        log_row.pages_fetched = pages_fetched
        log_row.jobs_found = jobs_found
        log_row.jobs_new = jobs_new
        log_row.jobs_updated = jobs_updated
        log_row.jobs_deduplicated = jobs_deduplicated
        log_row.requests_used = requests_used
        log_row.stopped_reason = stopped_reason
        log_row.error_message = error_message
        db.commit()


def _process_jobs_page(provider: str, jobs: list, seen_ids: set[str]) -> tuple[int, int, int, float]:
    jobs_new = 0
    jobs_updated = 0
    jobs_deduplicated = 0
    fresh_ratio = _compute_fresh_ratio(provider, jobs)
    with session_scope() as db:
        adapter = get_adapter(provider)
        for job in jobs:
            seen_ids.add(job.provider_job_id)
            state, _ = upsert_job(job, db_session=db, provider_adapter=adapter)
            if state == "inserted":
                jobs_new += 1
            elif state == "updated":
                jobs_updated += 1
            elif state == "duplicate":
                jobs_deduplicated += 1
    return jobs_new, jobs_updated, jobs_deduplicated, fresh_ratio


def _run_linear_page_sweep(provider: str, base_params: dict, seen_ids: set[str]) -> dict[str, int | str]:
    adapter = get_adapter(provider)
    page = max(int(base_params.get("page") or _page_start_for_provider(provider)), _page_start_for_provider(provider))
    pages_fetched = 0
    jobs_found = 0
    jobs_new = 0
    jobs_updated = 0
    jobs_deduplicated = 0
    requests_used = 0
    stop_reason = "no_more_pages"

    while True:
        if not confirm_quota(provider):
            stop_reason = "quota_threshold_hit"
            break

        params = dict(base_params)
        params["page"] = page
        jobs = adapter.fetch(params)
        requests_used += 1
        pages_fetched += 1

        if not jobs:
            stop_reason = "no_more_pages"
            break

        jobs_found += len(jobs)
        page_new, page_updated, page_deduplicated, fresh_ratio = _process_jobs_page(provider, jobs, seen_ids)
        jobs_new += page_new
        jobs_updated += page_updated
        jobs_deduplicated += page_deduplicated

        if fresh_ratio >= 0.80:
            stop_reason = "threshold_hit"
            break

        if len(jobs) < adapter.max_page_size:
            stop_reason = "no_more_pages"
            break

        page += 1
        sleep_seconds = _provider_sleep_seconds(provider)
        if sleep_seconds > 0:
            time.sleep(min(sleep_seconds, 10.0))

    return {
        "pages_fetched": pages_fetched,
        "jobs_found": jobs_found,
        "jobs_new": jobs_new,
        "jobs_updated": jobs_updated,
        "jobs_deduplicated": jobs_deduplicated,
        "requests_used": requests_used,
        "stopped_reason": stop_reason,
    }


def _run_provider_sweep(provider: str, *, category: str | None = None) -> dict[str, int | str | None]:
    definition = get_provider_definition(provider)
    controls = get_provider_controls(provider)
    if not controls.ingest_enabled:
        return {"status": "disabled", "provider": provider, "category": category}

    seen_ids: set[str] = set()
    totals = {
        "pages_fetched": 0,
        "jobs_found": 0,
        "jobs_new": 0,
        "jobs_updated": 0,
        "jobs_deduplicated": 0,
        "requests_used": 0,
        "stopped_reason": "no_more_pages",
    }

    if definition.sweep_mode == "category":
        stats = _run_linear_page_sweep(provider, {"category": [category] if category else []}, seen_ids)
        totals.update(stats)
        mark_unseen_jobs(provider=provider, category=category, seen_ids=seen_ids)
    elif definition.sweep_mode == "global":
        stats = _run_linear_page_sweep(provider, {}, seen_ids)
        totals.update(stats)
        mark_unseen_jobs(provider=provider, category=None, seen_ids=seen_ids)
    elif definition.sweep_mode == "matrix":
        stop_reason = "matrix_complete"
        for keyword in JOOBLE_KEYWORDS:
            for location in JOOBLE_LOCATIONS:
                stats = _run_linear_page_sweep(provider, {"keywords": keyword, "location": location}, seen_ids)
                for key in ("pages_fetched", "jobs_found", "jobs_new", "jobs_updated", "jobs_deduplicated", "requests_used"):
                    totals[key] += int(stats[key])
                stop_reason = str(stats["stopped_reason"])
                if stop_reason == "quota_threshold_hit":
                    totals["stopped_reason"] = stop_reason
                    mark_unseen_jobs(provider=provider, category=None, seen_ids=seen_ids)
                    return totals
        totals["stopped_reason"] = stop_reason
        mark_unseen_jobs(provider=provider, category=None, seen_ids=seen_ids)
    else:
        return {"status": "disabled", "provider": provider, "category": category}

    return totals


def _provider_due_for_dispatch(provider: str, *, category: str | None = None, interval_minutes: int) -> bool:
    if _lock_exists(provider, category):
        return False
    now = datetime.now(timezone.utc)
    with session_scope() as db:
        latest = (
            db.query(ProviderSyncLog)
            .filter(ProviderSyncLog.provider == provider, ProviderSyncLog.category == category)
            .order_by(ProviderSyncLog.started_at.desc())
            .first()
        )
    anchor = _sync_anchor(latest)
    if anchor is None:
        return True
    return (now - anchor) >= timedelta(minutes=max(int(interval_minutes), 5))


def _rotated_category_items(now: datetime) -> list[tuple[str, dict[str, int]]]:
    items = sorted(settings.JOB_SYNC_CATEGORY_SCHEDULE.items(), key=_category_sort_key)
    if not items:
        return []
    index = now.toordinal() % len(items)
    return [items[index]]


def queue_thin_results_sync(category: str) -> list[dict[str, str]]:
    """Queue provider sweeps that can help refill thin local job results."""
    # TODO: When a future provider needs special thin-result behavior, branch on its sweep mode here.
    queued: list[dict[str, str]] = []
    for provider in list_thin_sync_provider_names():
        definition = get_provider_definition(provider)
        if definition.sweep_mode == "category":
            if not _lock_exists(provider, category):
                sweep_category.delay(provider=provider, category=category)
                queued.append({"provider": provider, "category": category})
        elif definition.sweep_mode in {"global", "matrix"}:
            if not _lock_exists(provider, None):
                sweep_provider.delay(provider=provider)
                queued.append({"provider": provider, "category": ""})
    return queued


@celery_app.task(
    bind=True,
    name="app.tasks.job_sync.sweep_category",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def sweep_category(self, provider: str, category: str):
    """Fetch one provider/category slice, upsert rows, and expire unseen jobs for that category."""
    lock_key = _lock_key(provider, category)
    if not _acquire_lock(lock_key, int(settings.JOB_SYNC_LOCK_TTL_SECONDS)):
        return {"status": "skipped_locked", "provider": provider, "category": category}

    log_id = None
    try:
        definition = get_provider_definition(provider)
        if definition.sweep_mode != "category":
            return {"status": "unsupported_scope", "provider": provider, "category": category}

        log_id = _create_sync_log(provider=provider, category=category)
        stats = _run_provider_sweep(provider, category=category)
        if stats.get("status") == "disabled":
            _finalize_sync_log(log_id=log_id, stopped_reason="disabled")
            return stats

        _finalize_sync_log(log_id=log_id, **stats)
        status = "quota_threshold_hit" if stats.get("stopped_reason") == "quota_threshold_hit" else "completed"
        return {"status": status, "provider": provider, "category": category, **stats}
    except ProviderQuotaExceeded:
        _finalize_sync_log(log_id=log_id, stopped_reason="quota_threshold_hit")
        return {"status": "quota_threshold_hit", "provider": provider, "category": category}
    except Exception as exc:
        _finalize_sync_log(log_id=log_id, stopped_reason="error", error_message=str(exc))
        raise
    finally:
        _release_lock(lock_key)


@celery_app.task(
    bind=True,
    name="app.tasks.job_sync.sweep_provider",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def sweep_provider(self, provider: str):
    """Fetch one provider-wide sweep scope for global or matrix providers."""
    lock_key = _lock_key(provider, None)
    if not _acquire_lock(lock_key, int(settings.JOB_SYNC_LOCK_TTL_SECONDS)):
        return {"status": "skipped_locked", "provider": provider}

    log_id = None
    try:
        definition = get_provider_definition(provider)
        if definition.sweep_mode not in {"global", "matrix"}:
            return {"status": "unsupported_scope", "provider": provider}

        log_id = _create_sync_log(provider=provider, category=None)
        stats = _run_provider_sweep(provider, category=None)
        if stats.get("status") == "disabled":
            _finalize_sync_log(log_id=log_id, stopped_reason="disabled")
            return stats

        _finalize_sync_log(log_id=log_id, **stats)
        status = "quota_threshold_hit" if stats.get("stopped_reason") == "quota_threshold_hit" else "completed"
        return {"status": status, "provider": provider, **stats}
    except ProviderQuotaExceeded:
        _finalize_sync_log(log_id=log_id, stopped_reason="quota_threshold_hit")
        return {"status": "quota_threshold_hit", "provider": provider}
    except Exception as exc:
        _finalize_sync_log(log_id=log_id, stopped_reason="error", error_message=str(exc))
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
    """Queue scheduled provider sweeps based on the provider registry and controls."""
    if not settings.JOB_SYNC_ENABLED:
        return {"queued": []}

    queued: list[dict[str, str]] = []
    now = datetime.now(timezone.utc)
    # TODO: Add provider-specific dispatch rules here when a future provider needs a custom cadence.
    for provider in sorted(list_enabled_provider_names(control_name="scheduled")):
        definition = get_provider_definition(provider)
        controls = get_provider_controls(provider)
        if not controls.scheduled_enabled:
            continue
        if not confirm_quota(provider):
            continue

        if definition.sweep_mode == "category":
            category_items = sorted(settings.JOB_SYNC_CATEGORY_SCHEDULE.items(), key=_category_sort_key)
            if provider == "adzuna":
                category_items = _rotated_category_items(now)
            for category, config in category_items:
                interval = int(config.get("interval_minutes", definition.scheduled_interval_minutes or 60))
                if definition.scheduled_interval_minutes is not None:
                    interval = max(interval, int(definition.scheduled_interval_minutes))
                if not _provider_due_for_dispatch(provider, category=category, interval_minutes=interval):
                    continue
                sweep_category.delay(provider=provider, category=category)
                queued.append({"provider": provider, "category": category})
        elif definition.sweep_mode in {"global", "matrix"}:
            interval = max(int(definition.scheduled_interval_minutes or 60), 5)
            if not _provider_due_for_dispatch(provider, category=None, interval_minutes=interval):
                continue
            sweep_provider.delay(provider=provider)
            queued.append({"provider": provider, "category": ""})

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


@celery_app.task(
    bind=True,
    name="app.tasks.job_sync.backfill_job_link_health",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def backfill_job_link_health(self):
    """Refresh link-health and provenance metadata for existing active rows."""
    lock_key = _backfill_lock_key()
    if not _acquire_lock(lock_key, int(settings.JOB_SYNC_LOCK_TTL_SECONDS)):
        return {"status": "skipped_locked"}
    try:
        summary = backfill_job_health_batch()
        return {"status": "completed", **summary}
    finally:
        _release_lock(lock_key)


@celery_app.task(
    bind=True,
    name="app.tasks.job_sync.audit_stale_jobs",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def audit_stale_jobs(self):
    """Audit older listings for reposting behavior and stale/dead link outcomes."""
    lock_key = _stale_audit_lock_key()
    if not _acquire_lock(lock_key, int(settings.JOB_SYNC_LOCK_TTL_SECONDS)):
        return {"status": "skipped_locked"}
    try:
        summary = audit_stale_jobs_batch()
        return {"status": "completed", **summary}
    finally:
        _release_lock(lock_key)
