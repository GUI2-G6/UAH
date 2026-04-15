"""
Redis-backed parse queue for UAH resume parsing.

Architecture:
- Jobs are pushed to method-specific Redis lists (cloud/local/rules)
- A single worker coroutine polls queues with rotating key order for fairness
- Job status is tracked in Redis hash (uah:job_status:{job_id})
- Worker runs as a FastAPI background task on startup
- Falls back to direct in-process execution if Redis is unavailable

Queue entry format:
{
  "job_id": int,
  "resume_id": int,
  "user_id": int,
    "method": "cloud" | "local" | "rules",
  "enqueued_at": ISO timestamp,
  "attempt": int
}

Status hash fields: status, progress_stage, error_code, error_message,
                    enqueued_at, started_at, completed_at, attempt
"""

import asyncio
from datetime import datetime, timedelta, timezone
import importlib
import json
import logging
from typing import Any

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.parse_job import ParseJob
from app.services.parse_job_runner import run_parse_job
from app.services.resume_parser import is_retryable_cloud_parse_error, normalize_parse_method

logger = logging.getLogger(__name__)

_redis_client: Any | None = None
_worker_task: asyncio.Task | None = None
_in_flight_tasks: set[asyncio.Task] = set()

QUEUE_METHODS = ("cloud", "local", "rules")
_QUEUE_NAMES = settings.parse_queue_name_by_method
_QUEUE_NAME_TO_METHOD = {name: method for method, name in _QUEUE_NAMES.items()}
_CLAIM_KEY_PREFIX = f"{settings.PARSE_QUEUE_NAME}:claim"
_DEPTH_KEY_TOTAL = f"{settings.PARSE_QUEUE_NAME}:depth:total"
_DEPTH_KEY_BY_METHOD = {
    method: f"{settings.PARSE_QUEUE_NAME}:depth:{method}"
    for method in QUEUE_METHODS
}
_IN_FLIGHT_BY_METHOD: dict[str, int] = {method: 0 for method in QUEUE_METHODS}
_LAST_DISPATCH_AT_BY_METHOD: dict[str, datetime | None] = {method: None for method in QUEUE_METHODS}

_worker_state: dict[str, Any] = {
    "enabled": False,
    "running": False,
    "mode": "disabled",
    "redis_connected": False,
    "last_heartbeat": None,
    "last_queue_method": None,
    "in_flight_total": 0,
    "in_flight_by_method": {method: 0 for method in QUEUE_METHODS},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get_redis_client() -> Any | None:
    global _redis_client

    if not settings.REDIS_ENABLED:
        _worker_state["enabled"] = False
        _worker_state["mode"] = "disabled"
        return None

    _worker_state["enabled"] = True

    try:
        redis_async = importlib.import_module("redis.asyncio")
    except Exception as exc:
        logger.warning("redis.asyncio is unavailable: %s", exc)
        _worker_state["redis_connected"] = False
        return None

    if _redis_client is None:
        _redis_client = redis_async.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        await _redis_client.ping()
        _worker_state["redis_connected"] = True
        return _redis_client
    except Exception as exc:
        _worker_state["redis_connected"] = False
        _redis_client = None
        logger.warning("Redis unavailable at %s: %s", settings.REDIS_URL, exc)
        return None


def _concurrency_for_method(method: str) -> int:
    method_key = normalize_parse_method(method) or "local"
    attr = f"PARSE_QUEUE_CONCURRENCY_{method_key.upper()}"
    raw = getattr(settings, attr, 1)
    return max(int(raw), 1)


def _max_retries_for_method(method: str) -> int:
    method_key = normalize_parse_method(method) or "local"
    attr = f"PARSE_QUEUE_MAX_RETRIES_{method_key.upper()}"
    override = int(getattr(settings, attr, -1))
    if override >= 0:
        return override
    return max(int(settings.PARSE_QUEUE_MAX_RETRIES), 0)


def _retry_delay_seconds(method: str, next_attempt: int) -> int:
    method_key = normalize_parse_method(method) or "local"
    if method_key == "rules":
        return 0
    if method_key == "local":
        return max(2 * next_attempt, 1)
    return max(2 ** next_attempt, 1)


def _can_retry_job(method: str, error_code: str | None) -> bool:
    method_key = normalize_parse_method(method) or "local"
    if method_key == "cloud":
        return is_retryable_cloud_parse_error(error_code)
    if method_key == "rules":
        return False
    return True


def _mark_job_retry_state(job_id: int, status: str, progress_stage: str, error_code: str | None, error_message: str | None) -> None:
    db = SessionLocal()
    try:
        job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
        if not job or job.status == "cancelled":
            return
        job.status = status
        job.progress_stage = progress_stage
        job.error_code = error_code
        job.error_message = error_message
        db.commit()
    finally:
        db.close()


def _min_interval_for_method(method: str) -> int:
    method_key = normalize_parse_method(method) or "local"
    if method_key == "cloud":
        return max(int(getattr(settings, "PARSE_QUEUE_CLOUD_MIN_INTERVAL_SECONDS", 5)), 0)
    return 0


def _claim_key(job_id: int) -> str:
    return f"{_CLAIM_KEY_PREFIX}:{job_id}"


def _set_worker_inflight_state() -> None:
    _worker_state["in_flight_total"] = len(_in_flight_tasks)
    _worker_state["in_flight_by_method"] = {
        method: _IN_FLIGHT_BY_METHOD.get(method, 0) for method in QUEUE_METHODS
    }


async def _acquire_job_claim(client: Any, job_id: int) -> bool:
    try:
        claim_ttl = max(int(getattr(settings, "PARSE_QUEUE_CLAIM_TTL_SECONDS", 1800)), 60)
        claimed = await client.set(_claim_key(job_id), _now_iso(), ex=claim_ttl, nx=True)
        return bool(claimed)
    except Exception as exc:
        logger.warning("Failed to claim parse job %s: %s", job_id, exc)
        return False


async def _release_job_claim(client: Any | None, job_id: int) -> None:
    if client is None:
        return
    try:
        await client.delete(_claim_key(job_id))
    except Exception as exc:
        logger.debug("Failed to release claim for parse job %s: %s", job_id, exc)


async def _set_queue_depth(client: Any) -> int:
    depths = await _set_queue_depths(client)
    return int(depths.get("total", 0))


def _queue_name_for_method(method: str | None) -> str:
    normalized = normalize_parse_method(method) or "local"
    return _QUEUE_NAMES[normalized]


async def _set_queue_depths(client: Any) -> dict[str, int]:
    depths: dict[str, int] = {}
    total = 0
    for method in QUEUE_METHODS:
        queue_name = _QUEUE_NAMES[method]
        depth = int(await client.llen(queue_name))
        depths[method] = depth
        total += depth
        await client.set(_DEPTH_KEY_BY_METHOD[method], depth)

    depths["total"] = total
    await client.set(_DEPTH_KEY_TOTAL, total)
    return depths


async def _set_job_status(client: Any, job_id: int, fields: dict[str, Any]) -> None:
    mapping = {k: str(v) for k, v in fields.items() if v is not None}
    if mapping:
        await client.hset(f"uah:job_status:{job_id}", mapping=mapping)


async def enqueue_parse_job(job_id: int, resume_id: int, user_id: int, method: str) -> bool:
    client = await _get_redis_client()
    if client is None:
        return False

    normalized_method = normalize_parse_method(method) or "local"

    payload = {
        "job_id": job_id,
        "resume_id": resume_id,
        "user_id": user_id,
        "method": normalized_method,
        "enqueued_at": _now_iso(),
        "attempt": 0,
    }

    try:
        await client.rpush(_queue_name_for_method(normalized_method), json.dumps(payload))
        await _set_queue_depths(client)
        await _set_job_status(
            client,
            job_id,
            {
                "status": "queued",
                "progress_stage": "Queued...",
                "method": normalized_method,
                "enqueued_at": payload["enqueued_at"],
                "attempt": 0,
                "queue_name": _queue_name_for_method(normalized_method),
            },
        )
        return True
    except Exception as exc:
        logger.warning("Failed to enqueue parse job %s to Redis: %s", job_id, exc)
        _worker_state["redis_connected"] = False
        return False


async def get_queue_depth() -> int:
    client = await _get_redis_client()
    if client is None:
        return 0

    try:
        depths = await _set_queue_depths(client)
        return int(depths.get("total", 0))
    except Exception as exc:
        logger.warning("Could not read queue depth from Redis: %s", exc)
        _worker_state["redis_connected"] = False
        return 0


async def get_queue_depths() -> dict[str, int]:
    client = await _get_redis_client()
    if client is None:
        return {"total": 0, "cloud": 0, "local": 0, "rules": 0}

    try:
        return await _set_queue_depths(client)
    except Exception as exc:
        logger.warning("Could not read queue depths from Redis: %s", exc)
        _worker_state["redis_connected"] = False
        return {"total": 0, "cloud": 0, "local": 0, "rules": 0}


async def get_job_redis_status(job_id: int) -> dict | None:
    client = await _get_redis_client()
    if client is None:
        return None

    try:
        data = await client.hgetall(f"uah:job_status:{job_id}")
        return data or None
    except Exception as exc:
        logger.warning("Could not read Redis status for job %s: %s", job_id, exc)
        _worker_state["redis_connected"] = False
        return None


def get_worker_status() -> dict[str, Any]:
    return dict(_worker_state)


async def start_queue_worker() -> None:
    global _worker_task

    if not settings.REDIS_ENABLED:
        _worker_state["enabled"] = False
        _worker_state["mode"] = "disabled"
        return

    if _worker_task and not _worker_task.done():
        return

    _worker_state["enabled"] = True
    _worker_state["mode"] = "starting"
    _worker_task = asyncio.create_task(_worker_supervisor(), name="uah-parse-queue-worker")


async def stop_queue_worker() -> None:
    global _worker_task

    if _worker_task is not None:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        finally:
            _worker_task = None

    drain_seconds = max(int(getattr(settings, "PARSE_QUEUE_SHUTDOWN_DRAIN_SECONDS", 30)), 0)
    if _in_flight_tasks:
        done, pending = await asyncio.wait(_in_flight_tasks, timeout=drain_seconds)
        if pending:
            logger.warning("Cancelling %d in-flight parse tasks after drain timeout", len(pending))
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

    _worker_state["running"] = False
    _worker_state["mode"] = "stopped"
    _set_worker_inflight_state()


async def reconcile_stale_parse_jobs() -> dict[str, int]:
    """Mark stale in-progress parse jobs as failed after worker restart."""
    db = SessionLocal()
    try:
        stale_minutes = max(int(getattr(settings, "PARSE_QUEUE_STALE_JOB_MINUTES", 20)), 1)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
        stale_jobs = db.query(ParseJob).filter(
            ParseJob.status.in_(["parsing", "validating"]),
            ParseJob.updated_at < cutoff,
        ).all()

        for job in stale_jobs:
            job.status = "failed"
            job.error_code = "RECOVERED_AFTER_RESTART"
            job.error_message = "Job was recovered after worker restart and marked failed."
            job.progress_stage = "Failed"

        if stale_jobs:
            db.commit()

        return {
            "stale_marked_failed": len(stale_jobs),
        }
    except Exception as exc:
        logger.exception("Failed to reconcile stale parse jobs: %s", exc)
        return {
            "stale_marked_failed": 0,
        }
    finally:
        db.close()


async def _process_job(job_data: dict, queue_method: str | None = None) -> None:
    job_id = int(job_data["job_id"])
    attempt = int(job_data.get("attempt", 0))
    method = normalize_parse_method(job_data.get("method")) or queue_method or "local"
    job_data["method"] = method

    client = await _get_redis_client()
    if client is None:
        logger.warning("Skipping parse job %s because Redis is unavailable", job_id)
        return

    claimed = await _acquire_job_claim(client, job_id)
    if not claimed:
        logger.info("Skipping parse job %s because claim is already held", job_id)
        return

    try:
        await _set_job_status(
            client,
            job_id,
            {
                "status": "parsing",
                "progress_stage": f"Processing from {method} queue...",
                "method": method,
                "started_at": _now_iso(),
                "attempt": attempt,
            },
        )

        ok = await run_parse_job(job_id)
        if ok:
            await _set_job_status(
                client,
                job_id,
                {
                    "status": "success",
                    "progress_stage": "Complete",
                    "completed_at": _now_iso(),
                    "attempt": attempt,
                },
            )
            return

        db = SessionLocal()
        try:
            failed_job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
            failed_error_code = failed_job.error_code if failed_job else None
            failed_error_message = failed_job.error_message if failed_job else None
        finally:
            db.close()

        max_retries = _max_retries_for_method(method)
        if attempt < max_retries and _can_retry_job(method, failed_error_code):
            next_attempt = attempt + 1
            delay_seconds = _retry_delay_seconds(method, next_attempt)
            job_data["attempt"] = next_attempt

            await _set_job_status(
                client,
                job_id,
                {
                    "status": "retrying",
                    "progress_stage": f"Retrying in {delay_seconds}s",
                    "error_code": failed_error_code or "RETRY_SCHEDULED",
                    "error_message": failed_error_message or "Parser failed; retrying from Redis queue.",
                    "attempt": next_attempt,
                    "next_retry_delay_seconds": delay_seconds,
                    "retry_at": (_now_iso() if delay_seconds <= 0 else (datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)).isoformat()),
                },
            )
            _mark_job_retry_state(
                job_id=job_id,
                status="queued",
                progress_stage=f"Retrying in {delay_seconds}s",
                error_code=failed_error_code,
                error_message=failed_error_message,
            )

            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

            client = await _get_redis_client()
            if client is None:
                logger.warning("Retry enqueue skipped for job %s because Redis is unavailable", job_id)
                return

            await client.rpush(_queue_name_for_method(method), json.dumps(job_data))
            await _set_queue_depths(client)
            await _set_job_status(
                client,
                job_id,
                {
                    "status": "queued",
                    "progress_stage": "Queued for retry",
                    "method": method,
                    "attempt": next_attempt,
                    "queue_name": _queue_name_for_method(method),
                    "next_retry_delay_seconds": 0,
                },
            )
            return

        await _set_job_status(
            client,
            job_id,
            {
                "status": "failed",
                "progress_stage": "Failed",
                "error_code": "MAX_RETRIES_EXCEEDED",
                "error_message": "Parser failed after maximum retries.",
                "completed_at": _now_iso(),
                "attempt": attempt,
            },
        )
    finally:
        current_client = await _get_redis_client()
        await _release_job_claim(current_client, job_id)


def _dispatch_job(job_data: dict, queue_method: str) -> None:
    async def _runner() -> None:
        _IN_FLIGHT_BY_METHOD[queue_method] = _IN_FLIGHT_BY_METHOD.get(queue_method, 0) + 1
        _set_worker_inflight_state()
        try:
            await _process_job(job_data, queue_method=queue_method)
        finally:
            _IN_FLIGHT_BY_METHOD[queue_method] = max(_IN_FLIGHT_BY_METHOD.get(queue_method, 1) - 1, 0)
            _set_worker_inflight_state()

    task = asyncio.create_task(_runner(), name=f"uah-parse-job-{job_data.get('job_id')}")
    _in_flight_tasks.add(task)
    _set_worker_inflight_state()

    def _done_callback(done_task: asyncio.Task) -> None:
        _in_flight_tasks.discard(done_task)
        _set_worker_inflight_state()

    task.add_done_callback(_done_callback)


async def _worker_loop() -> None:
    method_cursor = 0

    while True:
        _worker_state["last_heartbeat"] = _now_iso()

        client = await _get_redis_client()
        if client is None:
            _worker_state["mode"] = "redis_unavailable"
            await asyncio.sleep(3)
            continue

        _worker_state["mode"] = "active"
        dispatched = False
        rotated_methods = list(QUEUE_METHODS[method_cursor:]) + list(QUEUE_METHODS[:method_cursor])

        for method in rotated_methods:
            if _IN_FLIGHT_BY_METHOD.get(method, 0) >= _concurrency_for_method(method):
                continue
            min_interval = _min_interval_for_method(method)
            last_dispatch_at = _LAST_DISPATCH_AT_BY_METHOD.get(method)
            if last_dispatch_at is not None and min_interval > 0:
                elapsed = (datetime.now(timezone.utc) - last_dispatch_at).total_seconds()
                if elapsed < min_interval:
                    continue

            queue_name = _QUEUE_NAMES[method]
            raw_payload = await client.lpop(queue_name)
            if not raw_payload:
                continue

            _worker_state["last_queue_method"] = method
            try:
                job_data = json.loads(raw_payload)
            except json.JSONDecodeError:
                logger.warning("Skipping invalid queue payload from %s: %s", queue_name, raw_payload)
                continue

            _dispatch_job(job_data, queue_method=method)
            _LAST_DISPATCH_AT_BY_METHOD[method] = datetime.now(timezone.utc)
            dispatched = True

        method_cursor = (method_cursor + 1) % len(QUEUE_METHODS)
        await _set_queue_depths(client)
        if not dispatched:
            await asyncio.sleep(1)


async def _worker_supervisor() -> None:
    backoff_seconds = 1
    _worker_state["running"] = True

    while True:
        try:
            await _worker_loop()
            backoff_seconds = 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            _worker_state["mode"] = "crashed"
            logger.exception("Parse queue worker crashed: %s", exc)
            await asyncio.sleep(backoff_seconds)
            backoff_seconds = min(backoff_seconds * 2, 30)
