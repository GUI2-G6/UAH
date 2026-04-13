from __future__ import annotations

from contextlib import nullcontext
from datetime import date, datetime, timezone
import logging

import httpx
from sqlalchemy import func

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


def _daily_request_count(provider_name: str, db, *, day: date | None = None) -> int:
    reference_day = day or datetime.now(timezone.utc).date()
    count = (
        db.query(func.coalesce(func.sum(QuotaUsage.request_count), 0))
        .filter(
            QuotaUsage.provider == provider_name,
            func.date(QuotaUsage.hour_bucket) == reference_day,
        )
        .scalar()
    )
    return int(count or 0)


def _confirm_daily_budget(provider_name: str, daily_request_budget: int, db) -> bool:
    if int(daily_request_budget or 0) <= 0:
        return True
    return _daily_request_count(provider_name, db) < max(int(daily_request_budget), 1)


def confirm_request_budget(
    *,
    provider_name: str,
    rate_limit_per_hour: int,
    daily_request_budget: int | None = None,
    db_session=None,
) -> bool:
    """Return True when a provider is still within its configured request budgets."""
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        if not _confirm_quota(provider_name, rate_limit_per_hour, db):
            return False
        if daily_request_budget is not None and not _confirm_daily_budget(provider_name, daily_request_budget, db):
            return False
        return True


def tracked_request(
    *,
    provider_name: str,
    rate_limit_per_hour: int,
    method: str,
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    json_body: dict | None = None,
    timeout_seconds: float = 10.0,
    daily_request_budget: int | None = None,
    db_session=None,
):
    """Perform one tracked outbound provider request and increment hourly quota usage."""
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        if not _confirm_quota(provider_name, rate_limit_per_hour, db):
            raise ProviderQuotaExceeded(
                f"Provider '{provider_name}' is at or above its configured hourly quota threshold."
            )
        if daily_request_budget is not None and not _confirm_daily_budget(provider_name, daily_request_budget, db):
            raise ProviderQuotaExceeded(
                f"Provider '{provider_name}' is at or above its configured daily request budget."
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
            return client.request(
                method=method.upper(),
                url=url,
                params=params,
                headers=headers,
                json=json_body,
            )
    except httpx.HTTPError as exc:
        logger.warning("Provider request failed for %s %s: %s", provider_name, url, exc)
        raise ProviderRequestFailed(str(exc)) from exc
