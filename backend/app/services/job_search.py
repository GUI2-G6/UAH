from __future__ import annotations

from datetime import timezone
from math import ceil

from sqlalchemy import or_

from app.api.routes import _build_jobs_filter_metadata_payload, _expand_category_for_muse, _parse_posted_after_input
from app.models.job import Job
from app.providers.registry import list_enabled_provider_names


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = " ".join((value or "").split())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _normalize_level_values(values: list[str]) -> list[str]:
    level_map = {
        "internship": "internship",
        "entry": "entry",
        "entry level": "entry",
        "mid": "mid",
        "mid level": "mid",
        "senior": "senior",
        "senior level": "senior",
        "manager": "manager",
        "management": "manager",
        "director": "director",
        "vp": "vp",
    }
    normalized: list[str] = []
    for value in values:
        clean = " ".join((value or "").strip().split())
        if not clean:
            continue
        mapped = level_map.get(clean.lower())
        normalized.append(mapped or clean)
    return _dedupe(normalized)


def _serialize_job(job: Job) -> dict:
    compat_id: int | str
    raw_provider_job_id = str(job.provider_job_id)
    compat_id = int(raw_provider_job_id) if raw_provider_job_id.isdigit() else raw_provider_job_id
    published_at_iso = job.published_at.astimezone(timezone.utc).isoformat() if job.published_at else None
    locations = [job.location] if job.location else []
    levels = [job.experience_level] if job.experience_level else []
    return {
        "local_id": str(job.id),
        "id": compat_id,
        "provider": job.provider,
        "provider_job_id": raw_provider_job_id,
        "provider_url": job.provider_url,
        "provider_url_status": job.provider_url_status,
        "job_url": job.provider_url,
        "apply_url": job.apply_url,
        "apply_url_status": job.apply_url_status,
        "apply_portal": job.apply_portal,
        "source_tags": list(job.source_tags or []),
        "title": job.title,
        "name": job.title,
        "short_name": job.title,
        "company": job.company,
        "company_url": job.company_url,
        "location": job.location,
        "locations": locations,
        "job_type": job.job_type,
        "type": job.job_type,
        "experience_level": job.experience_level,
        "levels": levels,
        "categories": list(job.categories or []),
        "tags": list(job.categories or []),
        "short_description": job.short_description or "",
        "description": job.description or "",
        "contents": job.description or "",
        "is_remote": bool(job.is_remote),
        "has_remote": bool(job.is_remote),
        "has_hybrid": False,
        "quality_score": float(job.quality_score or 0.0),
        "display_tier": job.display_tier,
        "staleness_status": job.staleness_status,
        "staleness_flags": list(job.staleness_flags or []),
        "published_at": published_at_iso,
        "publication_date": published_at_iso,
        "is_featured": bool(job.is_featured),
        "is_active": bool(job.is_active),
        "work_mode_reason": "remote" if job.is_remote else "onsite_or_unspecified",
    }


def search_local_jobs(
    *,
    db,
    categories: list[str] | None = None,
    locations: list[str] | None = None,
    is_remote: bool | None = None,
    experience_levels: list[str] | None = None,
    job_type: str | None = None,
    companies: list[str] | None = None,
    sort_by: str = "date_desc",
    tier: str = "active",
    page: int = 1,
    page_size: int = 20,
    q: str | None = None,
    posted_after: str | None = None,
) -> dict:
    """Query locally cached jobs only and return compatibility pagination metadata."""
    display_enabled_providers = list_enabled_provider_names(control_name="display")
    query = db.query(Job).filter(Job.is_active.is_(True)).filter(
        or_(Job.provider_url_status.is_(None), Job.provider_url_status != "bad")
    )
    if not display_enabled_providers:
        query = query.filter(False)
    else:
        query = query.filter(Job.provider.in_(display_enabled_providers))

    normalized_tier = (tier or "active").strip().lower()
    if normalized_tier == "active":
        query = query.filter(Job.display_tier == "active")
    elif normalized_tier == "aging":
        query = query.filter(Job.display_tier == "aging")
    else:
        query = query.filter(Job.display_tier.in_(["active", "aging", "stale"]))

    expanded_categories: list[str] = []
    for value in categories or []:
        expanded_categories.extend(_expand_category_for_muse(value))
    expanded_categories = _dedupe(expanded_categories)
    if expanded_categories:
        query = query.filter(Job.categories.overlap(expanded_categories))

    normalized_locations = _dedupe(list(locations or []))
    if normalized_locations:
        query = query.filter(or_(*[Job.location.ilike(f"%{value}%") for value in normalized_locations]))

    normalized_levels = _normalize_level_values(list(experience_levels or []))
    if normalized_levels:
        query = query.filter(Job.experience_level.in_(normalized_levels))

    if is_remote is not None:
        query = query.filter(Job.is_remote.is_(bool(is_remote)))

    if job_type:
        query = query.filter(Job.job_type == job_type)

    normalized_companies = _dedupe(list(companies or []))
    if normalized_companies:
        query = query.filter(or_(*[Job.company.ilike(f"%{value}%") for value in normalized_companies]))

    if q:
        normalized_query = f"%{' '.join(q.split())}%"
        query = query.filter(
            or_(
                Job.title.ilike(normalized_query),
                Job.company.ilike(normalized_query),
                Job.location.ilike(normalized_query),
                Job.description.ilike(normalized_query),
            )
        )
    else:
        normalized_query = ""

    posted_after_dt = _parse_posted_after_input(posted_after)
    if posted_after_dt is not None:
        query = query.filter(Job.published_at.is_not(None), Job.published_at >= posted_after_dt)

    normalized_sort = (sort_by or "date_desc").strip().lower()
    if normalized_sort == "date_asc":
        query = query.order_by(Job.published_at.asc().nullslast(), Job.quality_score.desc())
    elif normalized_sort == "quality_desc":
        query = query.order_by(Job.quality_score.desc(), Job.published_at.desc().nullslast())
    elif normalized_sort == "company_asc":
        query = query.order_by(Job.company.asc().nullslast(), Job.published_at.desc().nullslast())
    else:
        query = query.order_by(Job.published_at.desc().nullslast(), Job.quality_score.desc())

    total = query.count()
    page = max(int(page or 1), 1)
    page_size = max(min(int(page_size or 20), 100), 1)
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    jobs = [_serialize_job(row) for row in rows]
    has_more = total > (page * page_size)
    total_pages = max(ceil(total / page_size), 1) if total else 1
    filter_metadata = _build_jobs_filter_metadata_payload(db)

    return {
        "jobs": jobs,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": has_more,
        "source": "local_db",
        "total_jobs": total,
        "total_jobs_estimated": total,
        "total_pages": total_pages,
        "total_pages_estimated": total_pages,
        "has_next_page": has_more,
        "has_previous_page": page > 1,
        "totals_are_estimated": False,
        "total_estimate_strategy": "database_exact",
        "raw_total_jobs": total,
        "raw_total_pages": total_pages,
        "source_pages_scanned": 0,
        "filtered_out_count": 0,
        "guardrail_stop_reason": "local_db_only",
        "has_next_page_possible_raw": has_more,
        "has_more_source_pages": has_more,
        "source_page_count": total_pages,
        "window_start_page": page,
        "window_size": 1,
        "location_selection_strategy": "local_db_filter",
        "canonicalized_location_count": len(normalized_locations),
        "transformed_location_count": 0,
        "unmatched_location_count": 0,
        "strict_state_blocked_count": 0,
        "selected_state_diversity_count": 0,
        "accepted_by_concrete_location": len(jobs),
        "accepted_by_remote_override": 0,
        "accepted_by_hybrid_override": 0,
        "accepted_by_constraint_overlap": 0,
        "constraint_parse_high_confidence": 0,
        "constraint_parse_medium_confidence": 0,
        "constraint_parse_low_confidence": 0,
        "constraint_policy_remote_off": "n/a",
        "constraint_compatibility_enabled": False,
        "constraint_filter_min_confidence": "",
        "adaptive_chase_enabled": False,
        "adaptive_chase_extra_pages": 0,
        "effective_max_pages": 1,
        "effective_min_filtered_ratio": 0,
        "dropped_location_count": 0,
        "dropped_locations_sample": [],
        "dropped_invalid_url_count": 0,
        "url_validation_checked_count": 0,
        "url_validation_cache_hit_count": 0,
        "location_relaxed_fallback": False,
        "requested_locations_sample": normalized_locations[:12],
        "selected_locations_sample": normalized_locations[:12],
        "cache_hit": False,
        "keyword_query": normalized_query.strip("%"),
        "posted_after": posted_after_dt.isoformat() if posted_after_dt else "",
        "jobs_filter_metadata_version": filter_metadata.get("metadata_version"),
        "jobs_filter_metadata_hash": filter_metadata.get("metadata_hash"),
    }
