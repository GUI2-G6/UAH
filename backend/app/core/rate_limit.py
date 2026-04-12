from __future__ import annotations

from collections import deque
from math import ceil
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status

_RATE_LIMIT_BUCKETS: dict[str, deque[float]] = {}
_RATE_LIMIT_LOCK = Lock()


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


def _consume_rate_limit(bucket_key: str, limit: int, window_seconds: int) -> int | None:
    now = monotonic()
    cutoff = now - max(1, window_seconds)

    with _RATE_LIMIT_LOCK:
        bucket = _RATE_LIMIT_BUCKETS.setdefault(bucket_key, deque())
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= max(1, limit):
            retry_after = max(1, int(ceil(window_seconds - (now - bucket[0]))))
            return retry_after

        bucket.append(now)

        if not bucket:
            _RATE_LIMIT_BUCKETS.pop(bucket_key, None)

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
    with _RATE_LIMIT_LOCK:
        _RATE_LIMIT_BUCKETS.clear()
