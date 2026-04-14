from __future__ import annotations

import hashlib
import logging
import json
import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_developer
from app.db.session import get_db
from app.providers.registry import get_adapter, list_provider_statuses
from app.schemas.job import NormalizedJob
from app.services.job_board_debug import build_job_board_db_insights, build_job_board_overview
from app.services.job_search import search_local_jobs

router = APIRouter()
logger = logging.getLogger(__name__)


class ProviderProbeRequest(BaseModel):
    provider: str
    params: dict[str, Any] = Field(default_factory=dict)


class SearchProbeRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


def _enqueue_thin_results_sync(category: str) -> None:
    """Queue provider sweeps without importing worker dependencies at module import time."""
    from app.tasks.job_sync import queue_thin_results_sync

    queue_thin_results_sync(category)


def _payload_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _trim_jobs_payload(payload: dict[str, Any], sample_size: int = 5) -> dict[str, Any]:
    preview = dict(payload)
    jobs = list(preview.get("jobs") or [])
    preview["jobs"] = jobs[:sample_size]
    preview["jobs_truncated"] = max(len(jobs) - sample_size, 0)
    return preview


def _coerce_int(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _coerce_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return fallback


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_values = value
    else:
        raw_values = [value]
    items: list[str] = []
    for raw in raw_values:
        normalized = " ".join(str(raw or "").split())
        if normalized:
            items.append(normalized)
    return items


def _serialize_normalized_job(job: NormalizedJob) -> dict[str, Any]:
    return {
        "provider": job.provider,
        "provider_job_id": job.provider_job_id,
        "provider_url": job.provider_url,
        "apply_url": job.apply_url,
        "apply_host": job.apply_host,
        "apply_portal": job.apply_portal,
        "source_tags": list(job.source_tags or []),
        "title": job.title,
        "company": job.company,
        "company_url": job.company_url,
        "location": job.location,
        "is_remote": bool(job.is_remote),
        "job_type": job.job_type,
        "experience_level": job.experience_level,
        "categories": list(job.categories or []),
        "description": (job.description or "")[:320],
        "published_at": job.published_at.isoformat() if job.published_at else None,
    }


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


@router.get(
    "/jobs/debug/overview",
    tags=["jobs"],
    response_description="Read-only job board diagnostics overview for developer/admin tooling.",
)
def job_debug_overview(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin_or_developer),
):
    del current_user
    return build_job_board_overview(db)


@router.get(
    "/jobs/debug/db-insights",
    tags=["jobs"],
    response_description="Targeted DB insights for job board debugging.",
)
def job_debug_db_insights(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin_or_developer),
):
    del current_user
    return build_job_board_db_insights(db)


@router.post(
    "/jobs/debug/probe/provider",
    tags=["jobs"],
    response_description="Run a bounded read-only upstream provider probe.",
)
def probe_provider(
    request: ProviderProbeRequest,
    current_user=Depends(require_admin_or_developer),
):
    del current_user
    provider = " ".join((request.provider or "").strip().lower().split())
    if not provider:
        raise HTTPException(status_code=400, detail="Provider is required")

    try:
        adapter = get_adapter(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    started_at = time.perf_counter()
    try:
        results = adapter.fetch(dict(request.params or {}))
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        sample = [_serialize_normalized_job(job) for job in results[:5]]
        return {
            "status": "ok",
            "provider": provider,
            "latency_ms": latency_ms,
            "request_params": dict(request.params or {}),
            "item_count": len(results),
            "sample": sample,
            "sample_truncated": max(len(results) - len(sample), 0),
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
        return {
            "status": "error",
            "provider": provider,
            "latency_ms": latency_ms,
            "request_params": dict(request.params or {}),
            "item_count": 0,
            "sample": [],
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
        }


@router.post(
    "/jobs/debug/probe/local-search",
    tags=["jobs"],
    response_description="Replay the local jobs search path and return the UI payload shape.",
)
def probe_local_search(
    request: SearchProbeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin_or_developer),
):
    del current_user
    params = dict(request.params or {})
    started_at = time.perf_counter()
    payload = search_local_jobs(
        db=db,
        categories=_coerce_list(params.get("category")),
        locations=_coerce_list(params.get("location")),
        is_remote=params.get("is_remote") if params.get("is_remote") is None else _coerce_bool(params.get("is_remote"), False),
        experience_levels=_coerce_list(params.get("level") or params.get("experience_level")),
        job_type=(params.get("job_type") or None),
        companies=_coerce_list(params.get("company")),
        sort_by=str(params.get("sort_by") or "date_desc"),
        tier=str(params.get("tier") or "active"),
        page=_coerce_int(params.get("page"), 1),
        page_size=_coerce_int(params.get("page_size"), 20),
        q=(params.get("q") or None),
        posted_after=(params.get("posted_after") or None),
    )
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    preview = _trim_jobs_payload(payload)
    return {
        "status": "ok",
        "latency_ms": latency_ms,
        "request_params": params,
        "payload_hash": _payload_hash(payload),
        "response_preview": preview,
    }


@router.post(
    "/jobs/debug/probe/live-search",
    tags=["jobs"],
    response_description="Replay the live-source jobs search path and return the UI payload shape.",
)
async def probe_live_search(
    request: SearchProbeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin_or_developer),
):
    del current_user
    from app.api import routes as routes_api

    params = dict(request.params or {})
    started_at = time.perf_counter()
    payload = await routes_api.search_jobs(
        page=_coerce_int(params.get("page"), 1),
        page_size=_coerce_int(params.get("page_size"), 10),
        category=_coerce_list(params.get("category")) or None,
        catogory=_coerce_list(params.get("catogory")) or None,
        level=_coerce_list(params.get("level")) or None,
        location=_coerce_list(params.get("location")) or None,
        location_mode=(params.get("location_mode") or None),
        location_country_code=(params.get("location_country_code") or None),
        company=_coerce_list(params.get("company")) or None,
        q=(params.get("q") or None),
        posted_after=(params.get("posted_after") or None),
        include_remote=_coerce_bool(params.get("include_remote"), True),
        include_hybrid=_coerce_bool(params.get("include_hybrid"), True),
        db=db,
    )
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)
    preview = _trim_jobs_payload(payload)
    return {
        "status": "ok",
        "latency_ms": latency_ms,
        "request_params": params,
        "payload_hash": _payload_hash(payload),
        "response_preview": preview,
    }
