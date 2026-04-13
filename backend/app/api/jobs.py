from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.providers.registry import list_provider_statuses
from app.services.job_search import search_local_jobs

router = APIRouter()
logger = logging.getLogger(__name__)


def _enqueue_thin_results_sync(category: str) -> None:
    """Queue provider sweeps without importing worker dependencies at module import time."""
    from app.tasks.job_sync import queue_thin_results_sync

    queue_thin_results_sync(category)


@router.get(
    "/jobs/search",
    tags=["jobs"],
    response_description="Locally cached job results with compatibility pagination metadata.",
)
def search_jobs(
    page: int = Query(1, ge=1, description="UI page number (1-indexed)."),
    page_size: int = Query(20, ge=1, le=100, description="Number of jobs to return."),
    category: Optional[list[str]] = Query(None, description="One or more canonical UAH job categories."),
    catogory: Optional[list[str]] = Query(None, description="Backward-compatible misspelled alias of category."),
    location: Optional[list[str]] = Query(None, description="Optional location filters."),
    is_remote: bool | None = Query(None, description="When set, filter to remote or non-remote jobs."),
    experience_level: Optional[list[str]] = Query(None, description="Canonical experience levels."),
    level: Optional[list[str]] = Query(None, description="Legacy alias for experience_level."),
    job_type: str | None = Query(None, description="Optional job type filter."),
    company: Optional[list[str]] = Query(None, description="One or more company filters."),
    sort_by: str = Query("date_desc", description="Sort mode."),
    tier: str = Query("active", description="Freshness tier."),
    q: str | None = Query(None, description="Optional keyword query retained for frontend compatibility."),
    posted_after: str | None = Query(None, description="Optional published-at lower bound."),
    db: Session = Depends(get_db),
):
    """Query the local jobs catalog only and optionally enqueue a thin-results sweep."""
    requested_categories = list(category or []) + list(catogory or [])
    requested_levels = list(experience_level or []) + list(level or [])
    payload = search_local_jobs(
        db=db,
        categories=requested_categories,
        locations=list(location or []),
        is_remote=is_remote,
        experience_levels=requested_levels,
        job_type=job_type,
        companies=list(company or []),
        sort_by=sort_by,
        tier=tier,
        page=page,
        page_size=page_size,
        q=q,
        posted_after=posted_after,
    )

    note = None
    if len(payload.get("jobs") or []) < 10 and requested_categories:
        try:
            _enqueue_thin_results_sync(requested_categories[0])
            note = "results_thin_sync_triggered"
        except Exception as exc:
            logger.warning("Could not enqueue thin-results sync for %s: %s", requested_categories[0], exc)

    payload["note"] = note
    return payload


@router.get(
    "/providers/attribution",
    tags=["jobs"],
    response_description="Provider attribution metadata and current provider controls.",
)
def list_job_provider_attribution():
    """Return provider attribution details and resolved provider status flags."""
    return {"providers": list_provider_statuses()}
