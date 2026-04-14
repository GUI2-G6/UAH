from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import re
import uuid

from sqlalchemy import and_, func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.api.routes import _expand_category_for_muse
from app.core.config import settings
from app.db.session import session_scope
from app.models.job import Job
from app.providers.registry import get_adapter, get_provider_controls
from app.schemas.job import NormalizedJob
from app.services.job_location_normalization import normalize_job_location_country
from app.services.job_link_health import (
    build_source_tags,
    extract_url_host,
    job_link_needs_recheck,
    validate_job_link,
)

logger = logging.getLogger(__name__)

_SPAM_PUNCTUATION_RE = re.compile(r"[!$#?*]{3,}")
_COUNTRY_REPAIR_CITY_ONLY_LOCATIONS = {"berlin", "hamburg", "paris", "warsaw"}
_COUNTRY_REPAIR_AMBIGUOUS_CODES = {"CA", "DE", "GA", "IN", "ME", "OR", "XX"}
_DEDUP_NOISE_WORDS = (
    "senior",
    "sr",
    "jr",
    "junior",
    "lead",
    "staff",
    "principal",
    "associate",
    "remote",
    "hybrid",
    "inc",
    "llc",
    "ltd",
    "corp",
    "corporation",
    "co",
)

_DEDUP_HASH_CONSTRAINT_NAME = "idx_jobs_dedup_hash"


def compute_display_tier(*, is_active: bool, last_seen_at: datetime | None, reference_time: datetime | None = None) -> str:
    """Return the persisted display tier for a job based on freshness windows."""
    if not is_active:
        return "hidden"

    now = reference_time or datetime.now(timezone.utc)
    if last_seen_at is None:
        return "active"

    age = now - last_seen_at.astimezone(timezone.utc)
    if age < timedelta(days=30):
        return "active"
    if age <= timedelta(days=60):
        return "aging"
    return "stale"


def build_short_description(description: str | None, max_length: int = 300) -> str:
    """Create a condensed summary suitable for list/card rendering."""
    clean = " ".join((description or "").split())
    if not clean:
        return ""
    if len(clean) <= max_length:
        return clean
    return clean[: max_length - 1].rstrip() + "…"


def quality_check(job: NormalizedJob) -> tuple[bool, list[str]]:
    """Evaluate whether a normalized job is acceptable for local storage."""
    flags: list[str] = []
    title = (job.title or "").strip()
    company = (job.company or "").strip()
    description = " ".join((job.description or "").split())

    if not title or not company:
        return False, flags

    if len(description) < 100:
        return False, flags

    if any(ch.isalpha() for ch in title) and title.upper() == title:
        return False, flags
    if _SPAM_PUNCTUATION_RE.search(title):
        return False, flags

    if len(description) < 180:
        flags.append("short_description")
    if not (job.location or "").strip():
        flags.append("no_location")
    if not (job.company_url or "").strip():
        flags.append("no_company_url")
    if not job.categories:
        flags.append("missing_categories")
    if job.published_at is None:
        flags.append("missing_published_date")
    if not (job.provider_url or "").strip():
        flags.append("missing_provider_url")
    return True, flags


def compute_quality_score(job: NormalizedJob, flags: list[str]) -> float:
    """Compute a simple placeholder quality score for ranking and filtering."""
    score = 1.0
    flag_penalties = {
        "short_description": 0.12,
        "no_location": 0.10,
        "no_company_url": 0.08,
        "missing_categories": 0.08,
        "missing_published_date": 0.08,
        "missing_provider_url": 0.12,
        "provider_url_unknown": 0.06,
        "missing_apply_url": 0.04,
        "apply_url_unknown": 0.05,
        "apply_url_bad": 0.10,
        "suspect_reposted": 0.08,
        "suspect_stale": 0.18,
        "old_unchanged_listing": 0.12,
        "year_old_unchanged_listing": 0.16,
        "reposted_without_content_change": 0.06,
    }
    for flag in flags:
        score -= flag_penalties.get(flag, 0.05)

    if not job.job_type:
        score -= 0.05
    if not job.experience_level:
        score -= 0.05
    return max(0.0, min(round(score, 4), 1.0))


def compute_content_fingerprint(job: NormalizedJob) -> str:
    """Return a stable fingerprint for material job-content changes."""
    normalized_description = " ".join((job.description or "").split()).lower()
    normalized_categories = sorted({" ".join((value or "").split()).lower() for value in (job.categories or []) if value})
    payload = "\n".join(
        [
            " ".join((job.title or "").split()).lower(),
            " ".join((job.company or "").split()).lower(),
            " ".join((job.location or "").split()).lower(),
            " ".join((job.job_type or "").split()).lower(),
            " ".join((job.experience_level or "").split()).lower(),
            "|".join(normalized_categories),
            normalized_description,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_dedup_hash(title: str | None, company: str | None) -> str | None:
    """Return a normalized cross-provider dedup hash from title and company."""
    if not title or not company:
        return None

    def normalize(value: str) -> str:
        cleaned = value.lower().strip()
        cleaned = re.sub(r"[^\w\s]", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        for noise in _DEDUP_NOISE_WORDS:
            cleaned = re.sub(rf"\b{noise}\b", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()

    normalized_title = normalize(title)
    normalized_company = normalize(company)
    if not normalized_title or not normalized_company:
        return None
    return hashlib.md5(f"{normalized_title}|{normalized_company}".encode("utf-8")).hexdigest()


def _merge_unique_values(*collections: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for collection in collections:
        for value in collection or []:
            normalized = " ".join((value or "").split())
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(normalized)
    return result


def _normalized_job_from_row(row: Job) -> NormalizedJob:
    return NormalizedJob(
        provider=row.provider,
        provider_job_id=row.provider_job_id,
        provider_url=row.provider_url,
        apply_url=row.apply_url,
        apply_host=row.apply_host,
        apply_portal=row.apply_portal,
        source_tags=list(row.source_tags or []),
        title=row.title,
        company=row.company,
        company_url=row.company_url,
        location=row.location,
        is_remote=bool(row.is_remote),
        job_type=row.job_type,
        experience_level=row.experience_level,
        categories=list(row.categories or []),
        description=row.description,
        published_at=row.published_at,
    )


def _evaluate_job_link_health(job: NormalizedJob, *, provider_adapter) -> dict:
    provider_url = (job.provider_url or "").strip() or None
    provider_check = validate_job_link(
        provider_url,
        classifier=lambda status_code, body_text: provider_adapter.classify_landing_page_verdict(
            url=provider_url,
            status_code=status_code,
            body_text=body_text,
        ),
    )

    apply_url = (job.apply_url or "").strip() or None
    apply_host = (job.apply_host or "").strip() or None
    apply_portal = (job.apply_portal or "").strip().lower() or "missing"
    apply_status = "missing"
    apply_checked_at = None
    apply_error = None
    flags: list[str] = []

    if provider_check.status == "good":
        resolved = provider_adapter.resolve_apply_details(
            landing_url=provider_url,
            final_url=provider_check.final_url,
            body_text=provider_check.body_preview,
        )
        apply_url = (resolved.get("apply_url") or apply_url or "").strip() or None
        apply_host = (resolved.get("apply_host") or apply_host or extract_url_host(apply_url) or "").strip() or None
        apply_portal = (
            (resolved.get("apply_portal") or "").strip().lower()
            or (job.apply_portal or "").strip().lower()
            or provider_adapter.classify_apply_portal(apply_url)
        )
        if apply_url:
            apply_check = validate_job_link(apply_url)
            apply_status = apply_check.status
            apply_checked_at = apply_check.checked_at
            apply_error = apply_check.error
            if apply_status == "bad":
                flags.append("apply_url_bad")
            elif apply_status == "unknown":
                flags.append("apply_url_unknown")
        else:
            apply_status = "missing"
            apply_portal = "missing"
            flags.append("missing_apply_url")
    elif provider_check.status == "unknown":
        flags.append("provider_url_unknown")
    else:
        flags.append("provider_url_bad")

    source_tags = _merge_unique_values(
        list(job.source_tags or []),
        build_source_tags(
            provider=job.provider,
            provider_url=provider_url,
            apply_url=apply_url,
            apply_portal=apply_portal,
        ),
    )

    return {
        "provider_url_status": provider_check.status,
        "provider_url_checked_at": provider_check.checked_at,
        "provider_url_error": provider_check.error,
        "apply_url": apply_url,
        "apply_host": apply_host or extract_url_host(apply_url),
        "apply_portal": apply_portal or "missing",
        "apply_url_status": apply_status,
        "apply_url_checked_at": apply_checked_at,
        "apply_url_error": apply_error,
        "source_tags": source_tags,
        "flags": flags,
    }


def _evaluate_staleness(existing: Job | None, job: NormalizedJob, *, link_health: dict, reference_time: datetime) -> dict:
    first_published_at = existing.first_published_at if existing is not None else None
    if first_published_at is None:
        first_published_at = existing.published_at if existing is not None else None
    if first_published_at is None:
        first_published_at = job.published_at
    elif job.published_at is not None:
        first_published_at = min(first_published_at, job.published_at)

    fingerprint = compute_content_fingerprint(job)
    content_changed = (
        existing is None
        or not (existing.content_fingerprint or "").strip()
        or existing.content_fingerprint != fingerprint
    )
    last_content_change_at = (
        reference_time
        if content_changed
        else (existing.last_content_change_at if existing is not None else None) or reference_time
    )
    effective_last_updated_at = compute_effective_last_updated_at(
        existing=existing,
        job=job,
        content_changed=content_changed,
        reference_time=reference_time,
    )

    repost_count = int(existing.repost_count or 0) if existing is not None else 0
    flags: list[str] = []
    published_bumped = (
        existing is not None
        and existing.published_at is not None
        and job.published_at is not None
        and job.published_at > existing.published_at
    )
    if published_bumped and not content_changed:
        repost_count += 1
        flags.append("reposted_without_content_change")

    age_anchor = first_published_at or job.published_at
    age_days = 0
    if age_anchor is not None:
        age_days = max((reference_time - age_anchor.astimezone(timezone.utc)).days, 0)
    old_unchanged_cutoff = reference_time - timedelta(days=max(int(settings.JOB_STALE_MAX_UNCHANGED_DAYS), 1))
    is_old_unchanged_listing = bool(
        age_anchor is not None
        and age_anchor.astimezone(timezone.utc) <= old_unchanged_cutoff
        and (effective_last_updated_at is None or effective_last_updated_at <= old_unchanged_cutoff)
    )

    staleness_status = "fresh"
    if is_old_unchanged_listing:
        staleness_status = "trimmed_old_unchanged"
        flags.append("year_old_unchanged_listing")
    elif link_health["provider_url_status"] == "bad":
        staleness_status = "confirmed_stale"
        flags.append("provider_url_bad")
    elif age_days >= max(int(settings.JOB_STALE_AUDIT_AGE_DAYS), 1) and published_bumped and not content_changed:
        staleness_status = "suspect_reposted"
    elif age_days >= max(int(settings.JOB_STALE_AUDIT_ESCALATION_DAYS), 1) and not content_changed:
        flags.append("old_unchanged_listing")
        staleness_status = "suspect_stale"

    if link_health["apply_url_status"] == "bad":
        if age_days >= max(int(settings.JOB_STALE_AUDIT_ESCALATION_DAYS), 1) and repost_count >= 2 and not content_changed:
            staleness_status = "confirmed_stale"
        elif staleness_status != "confirmed_stale":
            staleness_status = "suspect_stale"
    if staleness_status == "suspect_reposted":
        flags.append("suspect_reposted")
    elif staleness_status == "suspect_stale":
        flags.append("suspect_stale")

    return {
        "first_published_at": first_published_at,
        "content_fingerprint": fingerprint,
        "last_content_change_at": last_content_change_at,
        "effective_last_updated_at": effective_last_updated_at,
        "staleness_status": staleness_status,
        "staleness_flags": flags,
        "staleness_checked_at": reference_time,
        "repost_count": repost_count,
    }


def compute_effective_last_updated_at(
    *,
    existing: Job | None,
    job: NormalizedJob,
    content_changed: bool,
    reference_time: datetime,
) -> datetime | None:
    """Return the best known substantive-update timestamp for stale trimming."""
    if content_changed:
        return reference_time

    candidates = [
        existing.last_content_change_at if existing is not None else None,
        job.published_at,
        existing.published_at if existing is not None else None,
        existing.first_published_at if existing is not None else None,
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        return candidate.astimezone(timezone.utc)
    return None


def _build_job_payload(job: NormalizedJob, *, existing: Job | None, link_health: dict, reference_time: datetime) -> dict:
    staleness = _evaluate_staleness(existing, job, link_health=link_health, reference_time=reference_time)
    quality_ok, quality_flags = quality_check(job)
    if not quality_ok:
        return {"should_store": False}

    if link_health["provider_url_status"] == "bad":
        return {"should_store": False}

    categories = list(dict.fromkeys([value for value in (job.categories or []) if value]))
    short_description = build_short_description(job.description)
    location_country_code, location_country_name = normalize_job_location_country(job.location)
    combined_quality_flags = _merge_unique_values(
        quality_flags,
        list(link_health.get("flags") or []),
        list(staleness.get("staleness_flags") or []),
    )

    is_active = staleness["staleness_status"] not in {"confirmed_stale", "trimmed_old_unchanged"}
    display_tier = compute_display_tier(is_active=is_active, last_seen_at=reference_time, reference_time=reference_time)
    quality_score = compute_quality_score(job, combined_quality_flags)

    return {
        "should_store": True,
        "payload": {
            "id": existing.id if existing is not None else uuid.uuid4(),
            "provider": job.provider,
            "provider_job_id": job.provider_job_id,
            "provider_url": job.provider_url,
            "provider_url_status": link_health["provider_url_status"],
            "provider_url_checked_at": link_health["provider_url_checked_at"],
            "provider_url_error": link_health["provider_url_error"],
            "apply_url": link_health["apply_url"],
            "apply_host": link_health["apply_host"],
            "apply_portal": link_health["apply_portal"],
            "apply_url_status": link_health["apply_url_status"],
            "apply_url_checked_at": link_health["apply_url_checked_at"],
            "apply_url_error": link_health["apply_url_error"],
            "source_tags": list(link_health["source_tags"] or []),
            "title": job.title,
            "company": job.company,
            "company_url": job.company_url,
            "location": job.location,
            "location_country_code": location_country_code,
            "location_country_name": location_country_name,
            "is_remote": bool(job.is_remote),
            "job_type": job.job_type,
            "experience_level": job.experience_level,
            "categories": categories,
            "description": job.description,
            "short_description": short_description,
            "quality_score": quality_score,
            "quality_flags": combined_quality_flags,
            "consecutive_misses": 0,
            "first_seen_at": existing.first_seen_at if existing is not None else reference_time,
            "last_seen_at": reference_time,
            "published_at": job.published_at,
            "first_published_at": staleness["first_published_at"],
            "content_fingerprint": staleness["content_fingerprint"],
            "last_content_change_at": staleness["last_content_change_at"],
            "is_active": is_active,
            "is_featured": existing.is_featured if existing is not None else False,
            "display_tier": display_tier,
            "staleness_status": staleness["staleness_status"],
            "staleness_flags": list(staleness["staleness_flags"] or []),
            "staleness_checked_at": staleness["staleness_checked_at"],
            "repost_count": staleness["repost_count"],
            "dedup_hash": compute_dedup_hash(job.title, job.company),
        },
    }


def _resolve_active_dedup_owner(*, db, dedup_hash: str, existing: Job | None) -> Job | None:
    """Return the active row that currently owns a dedup hash, excluding the current row."""
    query = (
        db.query(Job)
        .filter(
            Job.dedup_hash == dedup_hash,
            Job.is_active.is_(True),
        )
        .order_by(Job.first_seen_at.asc(), Job.id.asc())
    )
    if existing is not None:
        query = query.filter(Job.id != existing.id)
    return query.first()


def _should_increment_same_provider_repost_count(*, existing: Job | None) -> bool:
    """Only bump the canonical row when a row first becomes a same-provider duplicate."""
    if existing is None:
        return True
    return bool(existing.dedup_hash)


def _refresh_cross_provider_duplicate(
    *,
    duplicate_owner: Job,
    existing: Job | None,
    job: NormalizedJob,
    reference_time: datetime,
) -> None:
    duplicate_owner.last_seen_at = reference_time
    duplicate_owner.consecutive_misses = 0
    duplicate_owner.display_tier = compute_display_tier(
        is_active=bool(duplicate_owner.is_active),
        last_seen_at=reference_time,
        reference_time=reference_time,
    )
    duplicate_owner.source_tags = _merge_unique_values(
        list(duplicate_owner.source_tags or []),
        [f"duplicate_provider:{job.provider}"],
    )
    if existing is not None and existing.id != duplicate_owner.id:
        existing.is_active = False
        existing.display_tier = compute_display_tier(
            is_active=False,
            last_seen_at=reference_time,
            reference_time=reference_time,
        )
        existing.last_seen_at = reference_time
        existing.consecutive_misses = 0
        existing.dedup_hash = None


def _job_upsert_values(payload: dict) -> dict:
    return {
        "provider_url": payload["provider_url"],
        "provider_url_status": payload["provider_url_status"],
        "provider_url_checked_at": payload["provider_url_checked_at"],
        "provider_url_error": payload["provider_url_error"],
        "apply_url": payload["apply_url"],
        "apply_host": payload["apply_host"],
        "apply_portal": payload["apply_portal"],
        "apply_url_status": payload["apply_url_status"],
        "apply_url_checked_at": payload["apply_url_checked_at"],
        "apply_url_error": payload["apply_url_error"],
        "source_tags": payload["source_tags"],
        "title": payload["title"],
        "company": payload["company"],
        "company_url": payload["company_url"],
        "location": payload["location"],
        "location_country_code": payload["location_country_code"],
        "location_country_name": payload["location_country_name"],
        "is_remote": payload["is_remote"],
        "job_type": payload["job_type"],
        "experience_level": payload["experience_level"],
        "categories": payload["categories"],
        "description": payload["description"],
        "short_description": payload["short_description"],
        "quality_score": payload["quality_score"],
        "quality_flags": payload["quality_flags"],
        "consecutive_misses": 0,
        "last_seen_at": payload["last_seen_at"],
        "published_at": payload["published_at"],
        "first_published_at": payload["first_published_at"],
        "content_fingerprint": payload["content_fingerprint"],
        "last_content_change_at": payload["last_content_change_at"],
        "is_active": payload["is_active"],
        "display_tier": payload["display_tier"],
        "staleness_status": payload["staleness_status"],
        "staleness_flags": payload["staleness_flags"],
        "staleness_checked_at": payload["staleness_checked_at"],
        "repost_count": payload["repost_count"],
        "dedup_hash": payload["dedup_hash"],
    }


def _build_job_upsert_statement(payload: dict):
    statement = insert(Job).values(**payload)
    return statement.on_conflict_do_update(
        index_elements=["provider", "provider_job_id"],
        set_=_job_upsert_values(payload),
    )


def _is_dedup_hash_integrity_error(exc: IntegrityError) -> bool:
    orig = getattr(exc, "orig", None)
    diag = getattr(orig, "diag", None)
    constraint_name = getattr(diag, "constraint_name", None)
    if constraint_name == _DEDUP_HASH_CONSTRAINT_NAME:
        return True
    return _DEDUP_HASH_CONSTRAINT_NAME in str(exc)


def upsert_job(job: NormalizedJob, db_session=None, provider_adapter=None) -> tuple[str, bool]:
    """Insert or update a normalized job and refresh its link-health and stale-listing metadata."""
    controls = get_provider_controls(job.provider)
    if not controls.ingest_enabled:
        return "disabled", False
    adapter = provider_adapter or get_adapter(job.provider)
    reference_time = datetime.now(timezone.utc)
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        existing = (
            db.query(Job)
            .filter(Job.provider == job.provider, Job.provider_job_id == job.provider_job_id)
            .first()
        )
        link_health = _evaluate_job_link_health(job, provider_adapter=adapter)
        payload_result = _build_job_payload(job, existing=existing, link_health=link_health, reference_time=reference_time)
        if not payload_result["should_store"]:
            return "rejected", False

        payload = payload_result["payload"]
        dedup_hash = payload.get("dedup_hash")
        duplicate_owner = None
        if settings.JOB_DEDUP_ENABLED and dedup_hash:
            duplicate_owner = _resolve_active_dedup_owner(db=db, dedup_hash=dedup_hash, existing=existing)

        if duplicate_owner is not None:
            if duplicate_owner.provider != job.provider:
                _refresh_cross_provider_duplicate(
                    duplicate_owner=duplicate_owner,
                    existing=existing,
                    job=job,
                    reference_time=reference_time,
                )
                db.commit()
                if settings.JOB_DEDUP_LOG_COLLISIONS:
                    logger.info(
                        "Cross-provider dedup matched %s/%s to %s/%s via %s",
                        job.provider,
                        job.provider_job_id,
                        duplicate_owner.provider,
                        duplicate_owner.provider_job_id,
                        dedup_hash,
                    )
                return "duplicate", False

            if existing is None or existing.id != duplicate_owner.id:
                if _should_increment_same_provider_repost_count(existing=existing):
                    duplicate_owner.repost_count = int(duplicate_owner.repost_count or 0) + 1
                payload["dedup_hash"] = None

        statement = _build_job_upsert_statement(payload)
        try:
            db.execute(statement)
        except IntegrityError as exc:
            db.rollback()
            if not _is_dedup_hash_integrity_error(exc):
                raise
            payload["dedup_hash"] = None
            statement = _build_job_upsert_statement(payload)
            db.execute(statement)
        db.commit()
        return ("updated", False) if existing is not None else ("inserted", True)


def refresh_existing_job_health(job_row: Job, *, db_session=None, provider_adapter=None, force_recheck: bool = False, reference_time: datetime | None = None) -> str:
    """Refresh link-health and staleness fields for one stored job row."""
    adapter = provider_adapter or get_adapter(job_row.provider)
    now = reference_time or datetime.now(timezone.utc)
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        row = job_row if db_session is not None else db.query(Job).filter(Job.id == job_row.id).first()
        if row is None:
            return "missing"

        if not force_recheck and not needs_link_health_backfill(row, reference_time=now):
            return "skipped"

        normalized = _normalized_job_from_row(row)
        link_health = _evaluate_job_link_health(normalized, provider_adapter=adapter)
        payload_result = _build_job_payload(normalized, existing=row, link_health=link_health, reference_time=now)
        if not payload_result["should_store"]:
            if link_health["provider_url_status"] == "bad":
                row.provider_url_status = link_health["provider_url_status"]
                row.provider_url_checked_at = link_health["provider_url_checked_at"]
                row.provider_url_error = link_health["provider_url_error"]
                row.staleness_status = "confirmed_stale"
                row.staleness_flags = _merge_unique_values(list(row.staleness_flags or []), ["provider_url_bad"])
                row.staleness_checked_at = now
                row.is_active = False
                row.display_tier = compute_display_tier(is_active=False, last_seen_at=row.last_seen_at, reference_time=now)
                db.commit()
                return "deactivated"
            return "skipped"

        payload = payload_result["payload"]
        for key, value in payload.items():
            setattr(row, key, value)
        db.commit()
        return "deactivated" if not row.is_active else "updated"


def needs_link_health_backfill(job_row: Job, *, reference_time: datetime | None = None) -> bool:
    """Return True when an existing row is missing or due for link-health refresh."""
    now = reference_time or datetime.now(timezone.utc)
    if job_link_needs_recheck(job_row.provider_url_checked_at, now=now):
        return True
    if not list(job_row.source_tags or []):
        return True
    if (job_row.apply_url or "").strip():
        return job_link_needs_recheck(job_row.apply_url_checked_at, now=now)
    return (job_row.apply_portal or "missing") in {"", "missing", "unknown"}


def needs_stale_audit(job_row: Job, *, reference_time: datetime | None = None) -> bool:
    """Return True when an existing row is old enough and due for stale/update auditing."""
    now = reference_time or datetime.now(timezone.utc)
    age_anchor = job_row.first_published_at or job_row.published_at
    if age_anchor is None:
        return False
    if age_anchor.astimezone(timezone.utc) > (now - timedelta(days=max(int(settings.JOB_STALE_AUDIT_AGE_DAYS), 1))):
        return False
    threshold = max(int(settings.JOB_STALE_AUDIT_RECHECK_HOURS), 1)
    return job_link_needs_recheck(job_row.staleness_checked_at, recheck_hours=threshold, now=now)


def _normalized_optional_text(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _normalized_optional_code(value: str | None) -> str:
    return _normalized_optional_text(value).upper()


def _repair_risk_location(location: str | None) -> bool:
    normalized = _normalized_optional_text(location)
    if not normalized:
        return False

    lowered = normalized.lower()
    pieces = [piece.strip() for piece in normalized.split(",") if piece.strip()]
    if lowered in _COUNTRY_REPAIR_CITY_ONLY_LOCATIONS:
        return True
    if lowered.startswith("washington dc") or "washington, dc" in lowered or "district of columbia" in lowered:
        return True
    if any(lowered.endswith(f", {code.lower()}") or f", {code.lower()}," in lowered for code in _COUNTRY_REPAIR_AMBIGUOUS_CODES if code != "XX"):
        return True
    if len(pieces) == 2 and ("county" in lowered or normalize_job_location_country(normalized)[0] == "US"):
        return True
    return False


def _country_backfill_row_key(job_row: Job) -> object:
    return getattr(job_row, "id", None) or ("memory", id(job_row))


def needs_country_normalization_backfill(job_row: Job, *, scope: str = "missing") -> bool:
    """Return True when a stored row should be included in a country-normalization backfill batch."""
    normalized_scope = (scope or "missing").strip().lower()
    if normalized_scope not in {"missing", "repair"}:
        raise ValueError(f"Unsupported country backfill scope: {scope}")
    if not bool(getattr(job_row, "is_active", True)):
        return False

    stored_code = _normalized_optional_code(getattr(job_row, "location_country_code", None))
    stored_name = _normalized_optional_text(getattr(job_row, "location_country_name", None))
    is_missing = not stored_code
    is_xx = stored_code == "XX"
    if normalized_scope == "missing":
        return is_missing

    location = getattr(job_row, "location", None)
    if is_missing or is_xx:
        return True
    if not _repair_risk_location(location):
        return False

    normalized_code, normalized_name = normalize_job_location_country(location)
    return stored_code != _normalized_optional_code(normalized_code) or stored_name != _normalized_optional_text(normalized_name)


def _country_backfill_query(db, *, scope: str):
    normalized_scope = (scope or "missing").strip().lower()
    normalized_code = func.upper(func.btrim(func.coalesce(Job.location_country_code, "")))
    normalized_location = func.lower(func.btrim(func.coalesce(Job.location, "")))
    is_blank_code = func.length(func.btrim(func.coalesce(Job.location_country_code, ""))) == 0

    query = db.query(Job).filter(Job.is_active.is_(True))
    if normalized_scope == "missing":
        return query.filter(is_blank_code).order_by(Job.last_seen_at.desc(), Job.id.asc())
    if normalized_scope != "repair":
        raise ValueError(f"Unsupported country backfill scope: {scope}")

    ambiguous_code_filters = []
    for code in ("CA", "DE", "GA", "IN", "ME", "OR"):
        ambiguous_code_filters.extend(
            [
                normalized_location.like(f"%, {code.lower()}"),
                normalized_location.like(f"%, {code.lower()},%"),
            ]
        )

    return (
        query.filter(
            or_(
                is_blank_code,
                normalized_code == "XX",
                and_(or_(*ambiguous_code_filters), normalized_code.in_(tuple(sorted(_COUNTRY_REPAIR_AMBIGUOUS_CODES - {"XX"})))),
                and_(
                    or_(
                        normalized_location.like("washington dc%"),
                        normalized_location.like("%washington, dc%"),
                        normalized_location.like("%district of columbia%"),
                    ),
                    normalized_code != "US",
                ),
                and_(normalized_location.like("%county%"), normalized_code != "US"),
                and_(normalized_location.in_(tuple(sorted(_COUNTRY_REPAIR_CITY_ONLY_LOCATIONS))), normalized_code.in_(("", "XX"))),
            )
        )
        .order_by(normalized_code.asc(), Job.last_seen_at.desc(), Job.id.asc())
    )


def backfill_job_country_normalization_batch(*, scope: str = "missing", batch_size: int | None = None, db_session=None) -> dict[str, int]:
    """Backfill normalized country metadata for active jobs in small maintenance batches."""
    normalized_scope = (scope or "missing").strip().lower()
    if normalized_scope not in {"missing", "repair"}:
        raise ValueError(f"Unsupported country backfill scope: {scope}")

    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        limit = max(int(batch_size or settings.JOB_COUNTRY_BACKFILL_BATCH_SIZE), 1)
        processed_row_ids: set[object] = set()
        summary = {
            "scanned": 0,
            "updated": 0,
            "unchanged": 0,
            "unresolved": 0,
            "batches_committed": 0,
        }

        while True:
            rows = _country_backfill_query(db, scope=normalized_scope).limit(limit * 6).all()
            candidates = [
                row
                for row in rows
                if _country_backfill_row_key(row) not in processed_row_ids
                and needs_country_normalization_backfill(row, scope=normalized_scope)
            ][:limit]
            if not candidates:
                logger.info("Country normalization backfill scope=%s completed with summary=%s", normalized_scope, summary)
                return summary

            batch_summary = {
                "scanned": 0,
                "updated": 0,
                "unchanged": 0,
                "unresolved": 0,
            }
            for row in candidates:
                batch_summary["scanned"] += 1
                location_country_code, location_country_name = normalize_job_location_country(row.location)
                next_code = _normalized_optional_code(location_country_code) or None
                next_name = _normalized_optional_text(location_country_name) or None
                current_code = _normalized_optional_code(row.location_country_code) or None
                current_name = _normalized_optional_text(row.location_country_name) or None

                if next_code is None:
                    batch_summary["unresolved"] += 1

                if current_code == next_code and current_name == next_name:
                    batch_summary["unchanged"] += 1
                    continue

                row.location_country_code = next_code
                row.location_country_name = next_name
                batch_summary["updated"] += 1

            db.commit()
            processed_row_ids.update(_country_backfill_row_key(row) for row in candidates)
            summary["scanned"] += batch_summary["scanned"]
            summary["updated"] += batch_summary["updated"]
            summary["unchanged"] += batch_summary["unchanged"]
            summary["unresolved"] += batch_summary["unresolved"]
            summary["batches_committed"] += 1
            logger.info(
                "Country normalization backfill batch scope=%s scanned=%s updated=%s unchanged=%s unresolved=%s",
                normalized_scope,
                batch_summary["scanned"],
                batch_summary["updated"],
                batch_summary["unchanged"],
                batch_summary["unresolved"],
            )


def backfill_job_health_batch(*, batch_size: int | None = None, db_session=None) -> dict[str, int]:
    """Refresh link-health metadata for stored active jobs in small maintenance batches."""
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        now = datetime.now(timezone.utc)
        limit = max(int(batch_size or settings.JOB_LINK_BACKFILL_BATCH_SIZE), 1)
        rows = (
            db.query(Job)
            .filter(Job.is_active.is_(True))
            .order_by(Job.provider_url_checked_at.asc().nullsfirst(), Job.last_seen_at.desc())
            .limit(limit * 4)
            .all()
        )
        candidates = [row for row in rows if needs_link_health_backfill(row, reference_time=now)][:limit]
        updated = 0
        deactivated = 0
        for row in candidates:
            result = refresh_existing_job_health(row, db_session=db, reference_time=now)
            if result == "updated":
                updated += 1
            elif result == "deactivated":
                deactivated += 1
        return {
            "scanned": len(candidates),
            "updated": updated,
            "deactivated": deactivated,
        }


def audit_stale_jobs_batch(*, batch_size: int | None = None, db_session=None) -> dict[str, int]:
    """Audit older active jobs for reposting and stale-link behavior."""
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=max(int(settings.JOB_STALE_AUDIT_AGE_DAYS), 1))
        limit = max(int(batch_size or settings.JOB_STALE_AUDIT_BATCH_SIZE), 1)
        rows = (
            db.query(Job)
            .filter(
                Job.is_active.is_(True),
                or_(
                    and_(Job.first_published_at.is_not(None), Job.first_published_at <= cutoff),
                    Job.published_at <= cutoff,
                ),
            )
            .order_by(Job.staleness_checked_at.asc().nullsfirst(), Job.first_published_at.asc().nullsfirst())
            .limit(limit * 4)
            .all()
        )
        candidates = [row for row in rows if needs_stale_audit(row, reference_time=now)][:limit]
        updated = 0
        deactivated = 0
        for row in candidates:
            result = refresh_existing_job_health(row, db_session=db, force_recheck=True, reference_time=now)
            if result == "updated":
                updated += 1
            elif result == "deactivated":
                deactivated += 1
        return {
            "scanned": len(candidates),
            "updated": updated,
            "deactivated": deactivated,
        }


def mark_unseen_jobs(provider: str, category: str, seen_ids: set[str], db_session=None) -> int:
    """Increment misses for jobs not observed during a provider/category sweep."""
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        category_tokens = _expand_category_for_muse(category) if category else []
        query = db.query(Job).filter(Job.provider == provider, Job.is_active.is_(True))
        if category_tokens:
            query = query.filter(Job.categories.overlap(category_tokens))
        if seen_ids:
            query = query.filter(~Job.provider_job_id.in_(list(seen_ids)))

        affected = 0
        now = datetime.now(timezone.utc)
        for row in query.all():
            row.consecutive_misses = int(row.consecutive_misses or 0) + 1
            if row.consecutive_misses >= max(int(settings.JOB_SYNC_SOFT_DELETE_MISSES), 1):
                row.is_active = False
            row.display_tier = compute_display_tier(
                is_active=bool(row.is_active),
                last_seen_at=row.last_seen_at,
                reference_time=now,
            )
            affected += 1

        if affected:
            db.commit()
        return affected


def run_cleanup(db_session=None) -> int:
    """Delete long-hidden jobs that are well beyond the configured retention window."""
    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(int(settings.JOB_SYNC_HARD_PURGE_DAYS), 1))
        rows = (
            db.query(Job)
            .filter(Job.is_active.is_(False), Job.last_seen_at < cutoff)
            .all()
        )
        deleted = len(rows)
        for row in rows:
            db.delete(row)
        if deleted:
            db.commit()
            logger.info("Deleted %s stale hidden jobs during cleanup.", deleted)
        return deleted
