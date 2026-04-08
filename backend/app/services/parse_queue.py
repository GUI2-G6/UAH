"""
Redis-backed parse queue for UAH resume parsing.

Architecture:
- Jobs are pushed to a Redis list (PARSE_QUEUE_NAME) as JSON
- A single worker coroutine pops jobs and processes them sequentially
- Job status is tracked in Redis hash (uah:job_status:{job_id})
- Worker runs as a FastAPI background task on startup
- Falls back to direct in-process execution if Redis is unavailable

Queue entry format:
{
  "job_id": int,
  "resume_id": int,
  "user_id": int,
  "method": "llm" | "rules",
  "enqueued_at": ISO timestamp,
  "attempt": int
}

Status hash fields: status, progress_stage, error_code, error_message,
                    enqueued_at, started_at, completed_at, attempt
"""

import asyncio
from datetime import datetime, timezone
import importlib
import json
import logging
from typing import Any

from app.core.config import settings
from app.services.parse_job_runner import run_parse_job

logger = logging.getLogger(__name__)

_redis_client: Any | None = None
_worker_task: asyncio.Task | None = None
_DEPTH_KEY = f"{settings.PARSE_QUEUE_NAME}:depth"

_worker_state: dict[str, Any] = {
    "enabled": False,
    "running": False,
    "mode": "disabled",
    "redis_connected": False,
    "last_heartbeat": None,
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
        logger.warning("Redis unavailable at %s: %s", settings.REDIS_URL, exc)
        return None


async def _set_queue_depth(client: Any) -> int:
    depth = int(await client.llen(settings.PARSE_QUEUE_NAME))
    await client.set(_DEPTH_KEY, depth)
    return depth


async def _set_job_status(client: Any, job_id: int, fields: dict[str, Any]) -> None:
    mapping = {k: str(v) for k, v in fields.items() if v is not None}
    if mapping:
        await client.hset(f"uah:job_status:{job_id}", mapping=mapping)


async def enqueue_parse_job(job_id: int, resume_id: int, user_id: int, method: str) -> bool:
    client = await _get_redis_client()
    if client is None:
        return False

    payload = {
        "job_id": job_id,
        "resume_id": resume_id,
        "user_id": user_id,
        "method": method,
        "enqueued_at": _now_iso(),
        "attempt": 0,
    }

    try:
        await client.rpush(settings.PARSE_QUEUE_NAME, json.dumps(payload))
        await _set_queue_depth(client)
        await _set_job_status(
            client,
            job_id,
            {
                "status": "queued",
                "progress_stage": "Queued...",
                "enqueued_at": payload["enqueued_at"],
                "attempt": 0,
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
        return await _set_queue_depth(client)
    except Exception as exc:
        logger.warning("Could not read queue depth from Redis: %s", exc)
        _worker_state["redis_connected"] = False
        return 0


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

    if _worker_task is None:
        return

    _worker_task.cancel()
    try:
        await _worker_task
    except asyncio.CancelledError:
        pass
    finally:
        _worker_task = None
        _worker_state["running"] = False
        _worker_state["mode"] = "stopped"


async def _process_job(job_data: dict) -> None:
    job_id = int(job_data["job_id"])
    attempt = int(job_data.get("attempt", 0))

    client = await _get_redis_client()
    if client is not None:
        await _set_job_status(
            client,
            job_id,
            {
                "status": "parsing",
                "progress_stage": "Processing from Redis queue...",
                "started_at": _now_iso(),
                "attempt": attempt,
            },
        )

    ok = await run_parse_job(job_id)
    if ok:
        if client is not None:
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

    if attempt < settings.PARSE_QUEUE_MAX_RETRIES:
        next_attempt = attempt + 1
        delay_seconds = 2 ** next_attempt
        job_data["attempt"] = next_attempt

        if client is not None:
            await _set_job_status(
                client,
                job_id,
                {
                    "status": "retrying",
                    "progress_stage": f"Retrying in {delay_seconds}s",
                    "error_code": "RETRY_SCHEDULED",
                    "error_message": "Parser failed; retrying from Redis queue.",
                    "attempt": next_attempt,
                },
            )

        await asyncio.sleep(delay_seconds)

        client = await _get_redis_client()
        if client is None:
            logger.warning("Retry enqueue skipped for job %s because Redis is unavailable", job_id)
            return

        await client.rpush(settings.PARSE_QUEUE_NAME, json.dumps(job_data))
        await _set_queue_depth(client)
        await _set_job_status(
            client,
            job_id,
            {
                "status": "queued",
                "progress_stage": "Queued for retry",
                "attempt": next_attempt,
            },
        )
        return

    if client is not None:
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


async def _worker_loop() -> None:
    while True:
        _worker_state["last_heartbeat"] = _now_iso()

        client = await _get_redis_client()
        if client is None:
            _worker_state["mode"] = "redis_unavailable"
            await asyncio.sleep(3)
            continue

        _worker_state["mode"] = "active"
        item = await client.blpop(settings.PARSE_QUEUE_NAME, timeout=5)

        if not item:
            await _set_queue_depth(client)
            continue

        _, raw_payload = item
        await _set_queue_depth(client)

        try:
            job_data = json.loads(raw_payload)
        except json.JSONDecodeError:
            logger.warning("Skipping invalid queue payload: %s", raw_payload)
            continue

        await _process_job(job_data)


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
