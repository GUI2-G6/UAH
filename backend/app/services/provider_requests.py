from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone
import logging

import httpx

from app.db.session import session_scope
from app.models.job import QuotaUsage

logger = logging.getLogger(__name__)


class ProviderQuotaExceeded(RuntimeError):
    """Raised when provider requests should stop before exhausting quota."""


class ProviderRequestFailed(RuntimeError):
    """Raised when the provider request fails in a retryable way."""


def _hour_bucket(now: datetime | None = None) -> datetime:
    reference = now or datetime.now(timezone.utc)
    return reference.replace(minute=0, second=0, microsecond=0)


def _confirm_quota(provider_name: str, rate_limit_per_hour: int, db) -> bool:
    bucket = _hour_bucket()
    row = (
        db.query(QuotaUsage)
        .filter(QuotaUsage.provider == provider_name, QuotaUsage.hour_bucket == bucket)
        .first()
    )
    if row is None:
        return True
    threshold = max(int(rate_limit_per_hour * 0.8), 1)
    return int(row.request_count or 0) < threshold


def tracked_request(
    *,
    provider_name: str,
    rate_limit_per_hour: int,
    method: str,
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout_seconds: float = 10.0,
    db_session=None,
):
    """Perform one tracked outbound provider request and increment hourly quota usage."""
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        if not _confirm_quota(provider_name, rate_limit_per_hour, db):
            raise ProviderQuotaExceeded(
                f"Provider '{provider_name}' is at or above its configured hourly quota threshold."
            )

        bucket = _hour_bucket()
        row = (
            db.query(QuotaUsage)
            .filter(QuotaUsage.provider == provider_name, QuotaUsage.hour_bucket == bucket)
            .first()
        )
        if row is None:
            row = QuotaUsage(provider=provider_name, hour_bucket=bucket, request_count=0)
            db.add(row)

        row.request_count = int(row.request_count or 0) + 1
        db.commit()

    try:
        with httpx.Client(timeout=max(float(timeout_seconds), 1.0)) as client:
            return client.request(method=method.upper(), url=url, params=params, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("Provider request failed for %s %s: %s", provider_name, url, exc)
        raise ProviderRequestFailed(str(exc)) from exc
