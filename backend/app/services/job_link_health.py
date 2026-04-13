from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
import time
from typing import Callable, Iterable
from urllib.parse import urlparse

import httpx

from app.core.config import settings

_JOB_URL_VALIDATION_CACHE: dict[str, dict[str, float | int | str | None]] = {}

INVALID_JOB_URL_STATUSES = {404, 410, 500, 502, 503, 504}
_GENERIC_BAD_BODY_PATTERNS = [
    re.compile(r"\bjob not found\b", re.IGNORECASE),
    re.compile(r"\bcould not be found\b", re.IGNORECASE),
    re.compile(r"\bno longer available\b", re.IGNORECASE),
    re.compile(r"\bposition has been filled\b", re.IGNORECASE),
    re.compile(r"\brole has been filled\b", re.IGNORECASE),
    re.compile(r"\bpage not found\b", re.IGNORECASE),
]
_BLOCKED_BODY_PATTERNS = [
    re.compile(r"\bcaptcha\b", re.IGNORECASE),
    re.compile(r"\baccess denied\b", re.IGNORECASE),
    re.compile(r"\bverify you are human\b", re.IGNORECASE),
    re.compile(r"\btemporarily blocked\b", re.IGNORECASE),
]
_PORTAL_HOST_MAP = (
    ("boards.greenhouse.io", "greenhouse"),
    ("greenhouse.io", "greenhouse"),
    ("jobs.lever.co", "lever"),
    ("lever.co", "lever"),
    ("myworkdayjobs.com", "workday"),
    ("workday.com", "workday"),
    ("smartrecruiters.com", "smartrecruiters"),
    ("icims.com", "icims"),
    ("jobs.ashbyhq.com", "ashby"),
    ("ashbyhq.com", "ashby"),
    ("jobvite.com", "jobvite"),
    ("bamboohr.com", "bamboohr"),
    ("workable.com", "workable"),
)


@dataclass
class UrlCheckResult:
    """Normalized outcome for one URL validation request."""

    url: str | None
    status: str
    checked_at: datetime
    status_code: int | None = None
    error: str | None = None
    final_url: str | None = None
    body_preview: str | None = None


def normalize_url_cache_key(url: str | None) -> str:
    """Return a stable cache key for one URL, or an empty string when invalid."""
    parsed = urlparse((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    normalized_path = parsed.path or "/"
    normalized_query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{normalized_path}{normalized_query}"


def extract_url_host(url: str | None) -> str | None:
    """Extract a lower-cased host name from a URL."""
    parsed = urlparse((url or "").strip())
    host = (parsed.netloc or "").strip().lower()
    return host or None


def classify_apply_portal(url: str | None) -> str:
    """Classify the downstream application portal based on final host name."""
    host = extract_url_host(url)
    if not host:
        return "missing"
    for candidate, portal in _PORTAL_HOST_MAP:
        if host == candidate or host.endswith(f".{candidate}"):
            return portal
    return "company_site"


def build_source_tags(*, provider: str, provider_url: str | None, apply_url: str | None, apply_portal: str | None) -> list[str]:
    """Build canonical provenance tags for a locally stored job."""
    tags: list[str] = []
    provider_name = (provider or "").strip().lower()
    if provider_name:
        tags.append(f"provider:{provider_name}")

    landing_host = extract_url_host(provider_url)
    if landing_host:
        tags.append(f"landing_host:{landing_host}")
        tags.append(f"landing_portal:{provider_name or landing_host}")

    apply_host = extract_url_host(apply_url)
    if apply_host:
        tags.append(f"apply_host:{apply_host}")

    normalized_apply_portal = (apply_portal or "").strip().lower()
    if normalized_apply_portal:
        tags.append(f"apply_portal:{normalized_apply_portal}")

    deduped: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        deduped.append(tag)
    return deduped


def classify_job_url_validation_verdict(
    status_code: int,
    body_text: str | None,
    *,
    extra_bad_patterns: Iterable[re.Pattern[str]] | None = None,
) -> str:
    """Classify one fetched page as good, bad, or unknown for job-link health."""
    normalized = (body_text or "").strip().lower()
    if status_code in INVALID_JOB_URL_STATUSES:
        return "bad"
    if status_code in {401, 403, 429}:
        return "unknown"
    for pattern in extra_bad_patterns or []:
        if pattern.search(normalized):
            return "bad"
    for pattern in _GENERIC_BAD_BODY_PATTERNS:
        if pattern.search(normalized):
            return "bad"
    for pattern in _BLOCKED_BODY_PATTERNS:
        if pattern.search(normalized):
            return "unknown"
    if 200 <= status_code < 400:
        return "good"
    return "unknown"


def job_link_needs_recheck(checked_at: datetime | None, *, recheck_hours: int | None = None, now: datetime | None = None) -> bool:
    """Return True when link-health metadata is missing or old enough to refresh."""
    if checked_at is None:
        return True
    reference_time = now or datetime.now(timezone.utc)
    threshold = max(int(recheck_hours or settings.JOB_LINK_RECHECK_HOURS), 1)
    return checked_at.astimezone(timezone.utc) <= (reference_time - timedelta(hours=threshold))


def _cleanup_job_url_validation_cache(now: float) -> None:
    expired_keys = [
        key for key, item in _JOB_URL_VALIDATION_CACHE.items()
        if float(item.get("expires_at", 0.0)) <= now
    ]
    for key in expired_keys:
        _JOB_URL_VALIDATION_CACHE.pop(key, None)

    max_keys = max(100, settings.JOBS_CACHE_MAX_KEYS * 4)
    if len(_JOB_URL_VALIDATION_CACHE) <= max_keys:
        return

    ordered = sorted(
        _JOB_URL_VALIDATION_CACHE.items(),
        key=lambda item: float(item[1].get("last_access", 0.0)),
    )
    for key, _ in ordered[: len(_JOB_URL_VALIDATION_CACHE) - max_keys]:
        _JOB_URL_VALIDATION_CACHE.pop(key, None)


def _get_job_url_validation_cache_entry(url: str | None) -> dict[str, float | int | str | None] | None:
    key = normalize_url_cache_key(url)
    if not key:
        return None

    now = time.monotonic()
    _cleanup_job_url_validation_cache(now)
    entry = _JOB_URL_VALIDATION_CACHE.get(key)
    if not entry:
        return None
    if float(entry.get("expires_at", 0.0)) <= now:
        _JOB_URL_VALIDATION_CACHE.pop(key, None)
        return None
    entry["last_access"] = now
    return entry


def _get_job_url_validation_cache_verdict(url: str | None) -> str | None:
    entry = _get_job_url_validation_cache_entry(url)
    if entry is None:
        return None
    verdict = str(entry.get("verdict") or "").strip().lower()
    return verdict or None


def _set_job_url_validation_cache_verdict(
    url: str | None,
    verdict: str,
    *,
    final_url: str | None = None,
    body_preview: str | None = None,
    status_code: int | None = None,
) -> None:
    key = normalize_url_cache_key(url)
    if not key:
        return

    normalized_verdict = (verdict or "").strip().lower()
    if normalized_verdict == "bad":
        ttl = max(1, int(settings.JOBS_URL_VALIDATION_BAD_TTL_SECONDS))
    elif normalized_verdict == "good":
        ttl = max(1, int(settings.JOBS_URL_VALIDATION_GOOD_TTL_SECONDS))
    else:
        normalized_verdict = "unknown"
        ttl = max(1, int(settings.JOBS_URL_VALIDATION_UNKNOWN_TTL_SECONDS))

    now = time.monotonic()
    _cleanup_job_url_validation_cache(now)
    _JOB_URL_VALIDATION_CACHE[key] = {
        "verdict": normalized_verdict,
        "expires_at": now + ttl,
        "last_access": now,
        "final_url": final_url,
        "body_preview": body_preview,
        "status_code": status_code,
    }


def validate_job_link(
    url: str | None,
    *,
    timeout_seconds: float | None = None,
    extra_bad_patterns: Iterable[re.Pattern[str]] | None = None,
    classifier: Callable[[int, str | None], str] | None = None,
    client: httpx.Client | None = None,
) -> UrlCheckResult:
    """Fetch one job URL with GET and return a cached health verdict."""
    checked_at = datetime.now(timezone.utc)
    normalized_url = (url or "").strip()
    if not normalized_url:
        return UrlCheckResult(
            url=url,
            status="unknown",
            checked_at=checked_at,
            error="missing_url",
        )

    cached_entry = _get_job_url_validation_cache_entry(normalized_url)
    if cached_entry is not None:
        return UrlCheckResult(
            url=normalized_url,
            status=str(cached_entry.get("verdict") or "unknown"),
            checked_at=checked_at,
            status_code=int(cached_entry["status_code"]) if cached_entry.get("status_code") is not None else None,
            final_url=str(cached_entry.get("final_url") or "") or None,
            body_preview=str(cached_entry.get("body_preview") or "") or None,
        )

    timeout = max(float(timeout_seconds or settings.JOBS_URL_VALIDATION_TIMEOUT_SECONDS), 0.5)
    own_client = client is None
    http_client = client or httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "UAH-JobHealth/1.0"},
    )
    try:
        response = http_client.get(normalized_url)
        body_preview = (response.text or "")[:6000]
        verdict = (
            classifier(response.status_code, body_preview)
            if classifier is not None
            else classify_job_url_validation_verdict(
                response.status_code,
                body_preview,
                extra_bad_patterns=extra_bad_patterns,
            )
        )
        _set_job_url_validation_cache_verdict(
            normalized_url,
            verdict,
            final_url=str(response.url),
            body_preview=body_preview,
            status_code=response.status_code,
        )
        return UrlCheckResult(
            url=normalized_url,
            status=verdict,
            checked_at=checked_at,
            status_code=response.status_code,
            final_url=str(response.url),
            body_preview=body_preview,
        )
    except Exception as exc:
        verdict = "unknown"
        _set_job_url_validation_cache_verdict(normalized_url, verdict)
        return UrlCheckResult(
            url=normalized_url,
            status=verdict,
            checked_at=checked_at,
            error=str(exc),
        )
    finally:
        if own_client:
            http_client.close()
