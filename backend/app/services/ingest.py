from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
import logging
import re
import uuid

from sqlalchemy.dialects.postgresql import insert

from app.api.routes import _expand_category_for_muse
from app.core.config import settings
from app.db.session import session_scope
from app.models.job import Job
from app.schemas.job import NormalizedJob

logger = logging.getLogger(__name__)

_SPAM_PUNCTUATION_RE = re.compile(r"[!$#?*]{3,}")


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
    }
    for flag in flags:
        score -= flag_penalties.get(flag, 0.05)

    if not job.job_type:
        score -= 0.05
    if not job.experience_level:
        score -= 0.05
    return max(0.0, min(round(score, 4), 1.0))


def upsert_job(job: NormalizedJob, db_session=None) -> tuple[str, bool]:
    """Insert or update a normalized job and refresh its freshness metadata."""
    should_store, flags = quality_check(job)
    if not should_store:
        return "rejected", False

    manager = nullcontext(db_session) if db_session is not None else session_scope()
    with manager as db:
        existing = (
            db.query(Job)
            .filter(Job.provider == job.provider, Job.provider_job_id == job.provider_job_id)
            .first()
        )

        now = datetime.now(timezone.utc)
        job_id = existing.id if existing is not None else uuid.uuid4()
        short_description = build_short_description(job.description)
        quality_score = compute_quality_score(job, flags)
        display_tier = compute_display_tier(is_active=True, last_seen_at=now, reference_time=now)
        categories = list(dict.fromkeys([value for value in (job.categories or []) if value]))

        payload = {
            "id": job_id,
            "provider": job.provider,
            "provider_job_id": job.provider_job_id,
            "provider_url": job.provider_url,
            "title": job.title,
            "company": job.company,
            "company_url": job.company_url,
            "location": job.location,
            "is_remote": bool(job.is_remote),
            "job_type": job.job_type,
            "experience_level": job.experience_level,
            "categories": categories,
            "description": job.description,
            "short_description": short_description,
            "quality_score": quality_score,
            "quality_flags": flags,
            "consecutive_misses": 0,
            "first_seen_at": existing.first_seen_at if existing is not None else now,
            "last_seen_at": now,
            "published_at": job.published_at,
            "is_active": True,
            "is_featured": existing.is_featured if existing is not None else False,
            "display_tier": display_tier,
        }

        statement = insert(Job).values(**payload)
        statement = statement.on_conflict_do_update(
            index_elements=["provider", "provider_job_id"],
            set_={
                "provider_url": payload["provider_url"],
                "title": payload["title"],
                "company": payload["company"],
                "company_url": payload["company_url"],
                "location": payload["location"],
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
                "is_active": True,
                "display_tier": payload["display_tier"],
            },
        )
        db.execute(statement)
        db.commit()
        return ("updated", False) if existing is not None else ("inserted", True)


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
