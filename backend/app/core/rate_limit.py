from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_RATE_LIMIT_KEY_PREFIX = "uah:rate_limit"
_redis_client: redis.Redis | None = None
_redis_warning_logged = False


def _normalize_key(value: str | int | None) -> str:
    normalized = str(value or "").strip().lower()
    return normalized[:160] if normalized else "unknown"


def get_request_client_ip(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").strip()
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first

    real_ip = (request.headers.get("x-real-ip") or "").strip()
    if real_ip:
        return real_ip

    if request.client and request.client.host:
        client_host = (request.client.host or "").strip()
        if client_host:
            return client_host

    return "unknown"


def _mark_redis_failure(exc: Exception) -> None:
    global _redis_client, _redis_warning_logged

    _redis_client = None
    if not _redis_warning_logged:
        logger.warning("Rate-limit Redis unavailable at %s: %s", settings.REDIS_URL, exc)
        _redis_warning_logged = True


def _get_redis_client() -> redis.Redis | None:
    global _redis_client, _redis_warning_logged

    if not settings.REDIS_ENABLED:
        return None

    try:
        if _redis_client is None:
            _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        _redis_client.ping()
        if _redis_warning_logged:
            logger.info("Rate-limit Redis connection restored")
            _redis_warning_logged = False
        return _redis_client
    except redis.RedisError as exc:
        _mark_redis_failure(exc)
        return None


def _consume_rate_limit(bucket_key: str, limit: int, window_seconds: int) -> int | None:
    client = _get_redis_client()
    if client is None:
        return None

    normalized_limit = max(1, int(limit))
    normalized_window = max(1, int(window_seconds))
    redis_key = f"{_RATE_LIMIT_KEY_PREFIX}:{bucket_key}"

    try:
        pipeline = client.pipeline()
        pipeline.incr(redis_key)
        pipeline.ttl(redis_key)
        current_count, ttl_seconds = pipeline.execute()

        current_count = int(current_count)
        ttl_seconds = int(ttl_seconds)

        if current_count == 1 or ttl_seconds < 0:
            client.expire(redis_key, normalized_window)
            ttl_seconds = normalized_window

        if current_count > normalized_limit:
            return max(1, ttl_seconds if ttl_seconds > 0 else normalized_window)
    except redis.RedisError as exc:
        _mark_redis_failure(exc)
        return None

    return None


def _raise_rate_limited(retry_after: int) -> None:
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Too many requests for this action. Try again in {retry_after}s.",
        headers={"Retry-After": str(retry_after)},
    )


def enforce_ip_rate_limit(scope: str, request: Request, *, limit: int, window_seconds: int) -> None:
    client_ip = _normalize_key(get_request_client_ip(request))
    retry_after = _consume_rate_limit(
        bucket_key=f"{scope}:ip:{client_ip}",
        limit=limit,
        window_seconds=window_seconds,
    )
    if retry_after is not None:
        _raise_rate_limited(retry_after)


def enforce_subject_rate_limit(scope: str, subject: str | int | None, *, limit: int, window_seconds: int) -> None:
    normalized_subject = _normalize_key(subject)
    if normalized_subject == "unknown":
        return

    retry_after = _consume_rate_limit(
        bucket_key=f"{scope}:subject:{normalized_subject}",
        limit=limit,
        window_seconds=window_seconds,
    )
    if retry_after is not None:
        _raise_rate_limited(retry_after)


def reset_rate_limit_state() -> None:
    global _redis_client, _redis_warning_logged

    client = _get_redis_client()
    _redis_client = None
    _redis_warning_logged = False
    if client is None:
        return

    try:
        keys = list(client.scan_iter(match=f"{_RATE_LIMIT_KEY_PREFIX}:*"))
        if keys:
            client.delete(*keys)
    except redis.RedisError as exc:
        _mark_redis_failure(exc)
