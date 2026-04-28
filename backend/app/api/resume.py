import asyncio
import logging
import os
import copy
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Path, Query, Body
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.user import User
from app.models.resume import Resume
from app.models.parse_job import ParseJob
from app.models.applicant_profile import ApplicantProfile
from app.api.deps import get_current_user
from app.core.config import settings
from app.schemas.resume import (
    ResumeUploadResponse, ResumeResponse, ResumeListItem,
    PortalCheckResponse, ParseRequest,
    ParseJobResponse, ParseJobStartResponse,
    ResumeReviewDraftUpdate, ResumeReviewDraftResponse,
    ResumeReviewConflictRequest, ResumeReviewConflictResponse,
    ResumeReviewApplyRequest, ResumeReviewApplyResponse,
)
from app.schemas.applicant_profile import ProfileResponse
from app.services.parse_job_runner import run_parse_job
from app.services.parse_queue import (
    enqueue_parse_job,
    get_job_redis_status,
    get_queue_depths,
    get_worker_status,
)
from app.services.resume_parser import (
    get_pipeline_availability,
    normalize_parse_method,
    parse_markdown_with_fallback,
    validate_and_fix,
    get_parse_input_text,
    check_portal_required,
)
from app.services.applicant_profile_canonical import (
    normalize_canonical_data,
    sync_profile_storage,
    merge_review_into_profile,
    generate_review_conflicts,
    build_profile_from_review,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resume", tags=["resume"])

MAX_RESUMES_PER_USER = 10
MAX_PROFILES_PER_USER = 10
MAX_FILE_SIZE = 5 * 1024 * 1024
UPLOAD_COOLDOWN_SECONDS = 30
REVIEW_SCHEMA_VERSION = "canonical_v1"
ALLOWED_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "application/acrobat",
    "applications/vnd.pdf",
    "text/pdf",
    "text/x-pdf",
    "application/octet-stream",
    "binary/octet-stream",
}

REVIEW_DRAFT_SCHEMA = {
    "version": REVIEW_SCHEMA_VERSION,
    "personal_fields": [
        {"key": "first_name", "label": "First Name"},
        {"key": "middle_name", "label": "Middle Name"},
        {"key": "last_name", "label": "Last Name"},
        {"key": "full_legal_name", "label": "Full Legal Name"},
        {"key": "preferred_name", "label": "Preferred Name"},
        {"key": "suffix", "label": "Suffix"},
        {"key": "email", "label": "Email", "type": "email"},
        {"key": "phone", "label": "Phone"},
        {"key": "address", "label": "Street Address", "full": True},
        {"key": "city", "label": "City"},
        {"key": "state", "label": "State"},
        {"key": "zip", "label": "ZIP"},
        {"key": "linkedin", "label": "LinkedIn", "type": "url"},
        {"key": "website", "label": "Website", "type": "url"},
    ],
    "skill_fields": [
        {"key": "technical", "label": "Technical Skills"},
        {"key": "languages", "label": "Languages"},
        {"key": "tools", "label": "Tools"},
        {"key": "soft_skills", "label": "Soft Skills"},
    ],
    "structured_sections": [
        {
            "key": "education",
            "pathStem": "education",
            "title": "Education",
            "fields": [
                {"key": "institution", "label": "Institution"},
                {"key": "degree", "label": "Degree"},
                {"key": "field_of_study", "label": "Field of Study"},
                {"key": "gpa", "label": "GPA"},
                {"key": "start_date", "label": "Start Date"},
                {"key": "end_date", "label": "End Date"},
                {"key": "honors", "label": "Honors", "kind": "inline-list", "full": True},
                {"key": "relevant_coursework", "label": "Relevant Coursework", "kind": "inline-list", "full": True},
            ],
        },
        {
            "key": "work_experience",
            "pathStem": "work_experience",
            "title": "Work Experience",
            "fields": [
                {"key": "company", "label": "Company"},
                {"key": "title", "label": "Title"},
                {"key": "location", "label": "Location"},
                {"key": "is_current", "label": "Current Role", "kind": "current-select"},
                {"key": "start_date", "label": "Start Date"},
                {"key": "end_date", "label": "End Date"},
                {"key": "bullets", "label": "Bullets", "kind": "line-list", "full": True},
            ],
        },
        {
            "key": "projects",
            "pathStem": "projects",
            "title": "Projects",
            "fields": [
                {"key": "name", "label": "Name"},
                {"key": "date", "label": "Date"},
                {"key": "description", "label": "Description", "kind": "textarea", "full": True},
                {"key": "technologies", "label": "Technologies", "kind": "inline-list", "full": True},
            ],
        },
        {
            "key": "certifications",
            "pathStem": "certifications",
            "title": "Certifications",
            "fields": [
                {"key": "name", "label": "Name"},
                {"key": "issuer", "label": "Issuer"},
                {"key": "date", "label": "Date", "full": True},
            ],
        },
    ],
    "extra_list_sections": [
        {"key": "awards", "label": "Awards"},
        {"key": "activities", "label": "Activities"},
        {"key": "volunteer", "label": "Volunteer"},
    ],
}


def _is_development_env() -> bool:
    env = (settings.ENVIRONMENT or "").strip().lower()
    env_alias = (os.getenv("ENV", "") or "").strip().lower()
    return env in {"development", "dev", "local"} or env_alias in {"development", "dev", "local"}


def _method_or_default(value: str | None) -> str:
    return normalize_parse_method(value) or "local"


def _looks_like_pdf(pdf_bytes: bytes) -> bool:
    if not pdf_bytes:
        return False
    trimmed = pdf_bytes.lstrip(b"\x00\x09\x0a\x0c\x0d\x20\xef\xbb\xbf")
    return trimmed.startswith(b"%PDF-")


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except Exception:
        return None


def _compute_elapsed_seconds(
    created_at: datetime | None,
    started_at: datetime | None,
    completed_at: datetime | None,
) -> int | None:
    start = started_at or created_at
    end = completed_at or datetime.now(timezone.utc)
    if start is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(int((end - start).total_seconds()), 0)


def _refresh_resume_validation_if_needed(resume: Resume) -> bool:
    if not isinstance(resume.structured_data, dict):
        return False

    validated = validate_and_fix(dict(resume.structured_data))
    recalculated_ready = bool(validated.get("_validation", {}).get("portal_ready", False))
    changed = (resume.portal_ready != recalculated_ready) or (validated != resume.structured_data)
    if changed:
        resume.structured_data = validated
        resume.portal_ready = recalculated_ready
    return changed


def _current_review_draft(resume: Resume) -> dict | None:
    draft = resume.review_draft if isinstance(resume.review_draft, dict) else None
    if draft:
        return copy.deepcopy(draft)
    if isinstance(resume.structured_data, dict):
        return copy.deepcopy(resume.structured_data)
    return None


def _set_review_draft(
    resume: Resume,
    review_draft: dict,
    status: str = "pending",
) -> None:
    resume.review_draft = validate_and_fix(copy.deepcopy(review_draft or {}))
    resume.review_status = status
    resume.review_updated_at = datetime.now(timezone.utc)


def _persist_parse_input_cache(
    resume: Resume,
    parse_text: str,
    method: str,
    source: str | None,
) -> None:
    resume.raw_markdown = parse_text
    resume.raw_markdown_method = method
    resume.raw_markdown_source = source
    resume.raw_markdown_updated_at = datetime.now(timezone.utc)


async def _build_queue_status_payload(
    db: Session,
    current_user: User,
    scope: str = "user",
    focus_method: str | None = None,
):
    active_statuses = ["queued", "parsing", "validating"]

    ordered_active_jobs = db.query(ParseJob).filter(
        ParseJob.status.in_(active_statuses),
    ).order_by(ParseJob.created_at.asc(), ParseJob.id.asc()).all()

    recent_jobs = db.query(ParseJob).filter(
        ParseJob.user_id == current_user.id,
    ).order_by(ParseJob.updated_at.desc()).limit(5).all()

    active_by_method = {"cloud": 0, "local": 0, "rules": 0}
    for job in ordered_active_jobs:
        active_by_method[_method_or_default(job.method)] += 1

    user_active_jobs = [job for job in ordered_active_jobs if job.user_id == current_user.id]
    user_active_by_method = {"cloud": 0, "local": 0, "rules": 0}
    for job in user_active_jobs:
        user_active_by_method[_method_or_default(job.method)] += 1

    focus_method_normalized = _method_or_default(focus_method)
    if not focus_method:
        latest_user_active_job = user_active_jobs[0] if user_active_jobs else None
        if latest_user_active_job:
            focus_method_normalized = _method_or_default(latest_user_active_job.method)

    active_in_focus_method = [
        job for job in ordered_active_jobs if _method_or_default(job.method) == focus_method_normalized
    ]
    user_active_in_focus_method = [
        job for job in active_in_focus_method if job.user_id == current_user.id
    ]
    latest_user_active_job = user_active_in_focus_method[0] if user_active_in_focus_method else None

    user_position = None
    if latest_user_active_job:
        for idx, job in enumerate(active_in_focus_method, start=1):
            if job.id == latest_user_active_job.id:
                user_position = idx
                break

    queue_depths = await get_queue_depths() if settings.REDIS_ENABLED else {
        "total": 0,
        "cloud": 0,
        "local": 0,
        "rules": 0,
    }

    latest_active_job_redis_status = None
    if settings.REDIS_ENABLED and latest_user_active_job:
        latest_active_job_redis_status = await get_job_redis_status(latest_user_active_job.id)

    requested_scope = (scope or "user").strip().lower()
    can_view_global = _is_development_env() and (
        bool(getattr(current_user, "is_admin", False)) or bool(getattr(current_user, "is_developer", False))
    )
    effective_scope = "global" if requested_scope == "global" and can_view_global else "user"
    environment_raw = (settings.ENVIRONMENT or "").strip().lower()
    if environment_raw in {"development", "dev", "local"}:
        environment_key = "dev"
        environment_label = "Dev"
    elif environment_raw in {"beta", "staging"}:
        environment_key = "beta"
        environment_label = "Beta"
    elif environment_raw in {"production", "prod"}:
        environment_key = "prod"
        environment_label = "Prod"
    else:
        environment_key = environment_raw or "unknown"
        environment_label = environment_key.upper() if environment_key != "unknown" else "Unknown"

    global_queue = None
    if effective_scope == "global":
        global_queue = {
            "active_count": len(ordered_active_jobs),
            "active_by_method": active_by_method,
            "entries": [
                {
                    "position": idx,
                    "job_id": job.id,
                    "user_id": job.user_id,
                    "resume_id": job.resume_id,
                    "method": _method_or_default(job.method),
                    "status": job.status,
                    "progress_stage": job.progress_stage,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                }
                for idx, job in enumerate(ordered_active_jobs[:25], start=1)
            ],
        }

    queue_depth_total = int(queue_depths.get("total", 0))
    pipeline_availability = await get_pipeline_availability()
    payload = {
        "scope": effective_scope,
        "requested_scope": requested_scope,
        "can_view_global": can_view_global,
        "environment": environment_key,
        "environment_label": environment_label,
        "redis_enabled": settings.REDIS_ENABLED,
        "queue_depth": queue_depth_total,
        "queue_depth_total": queue_depth_total,
        "queue_namespace": settings.parse_queue_name_for_method(focus_method_normalized),
        "queue_depth_by_method": {
            "cloud": int(queue_depths.get("cloud", 0)),
            "local": int(queue_depths.get("local", 0)),
            "rules": int(queue_depths.get("rules", 0)),
        },
        "worker_status": get_worker_status(),
        "cloud_behavior": {
            "ocr_model": "glm-ocr",
            "llm_model": settings.ZAI_LLM_MODEL,
            "provider_queue": "none",
            "provider_concurrency": "limited",
            "description": "Cloud pipeline uses web ZAI OCR and GLM-4.7-Flash; provider reachability and parse reliability are tracked separately so empty or malformed parses can surface as degraded even when the provider is reachable.",
        },
        "current_user": {
            "active_jobs": len(user_active_jobs),
            "active_jobs_by_method": user_active_by_method,
            "focus_method": focus_method_normalized,
            "active_job_position": user_position,
            "active_job_total": len(active_in_focus_method),
            "position_scope_label": f"{environment_label} {focus_method_normalized} queue",
            "latest_active_job_id": latest_user_active_job.id if latest_user_active_job else None,
            "latest_active_job_method": _method_or_default(latest_user_active_job.method) if latest_user_active_job else None,
            "latest_active_job_status": latest_user_active_job.status if latest_user_active_job else None,
            "recent_jobs": [
                {
                    "id": job.id,
                    "method": _method_or_default(job.method),
                    "status": job.status,
                    "progress_stage": job.progress_stage,
                    "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                }
                for job in recent_jobs
            ],
        },
        "global_metrics": {
            "active_total": len(ordered_active_jobs),
            "active_by_method": active_by_method,
            "queued_total": queue_depth_total,
            "queued_by_method": {
                "cloud": int(queue_depths.get("cloud", 0)),
                "local": int(queue_depths.get("local", 0)),
                "rules": int(queue_depths.get("rules", 0)),
            },
            "load_total": len(ordered_active_jobs) + queue_depth_total,
        },
        "pipeline_availability": pipeline_availability,
        "local_queue_note": "Local queue load matters most when UAH parses with Local AI.",
        "global_queue": global_queue,
        "latest_active_job_redis_status": latest_active_job_redis_status,
    }
    return payload


@router.post("/upload", response_model=ResumeUploadResponse, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a resume PDF and store it for later parsing.

    Accepts a PDF file, enforces upload limits/cooldowns, and stores the
    original PDF. OCR/text preparation happens during parse execution so the
    selected parse method controls downstream dependencies.

    Response codes:
    - 201: Resume uploaded successfully.
    - 400: File type invalid or file exceeds max size.
    - 429: Upload rate or per-user resume limit exceeded.
    """
    file_name = os.path.basename((file.filename or "").strip())
    if not file_name or not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type and content_type not in ALLOWED_PDF_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Uploaded file must use a PDF content type")

    resume_count = db.query(func.count(Resume.id)).filter(Resume.user_id == current_user.id).scalar()
    if resume_count >= MAX_RESUMES_PER_USER:
        raise HTTPException(status_code=429, detail=f"Max {MAX_RESUMES_PER_USER} resumes allowed, delete one first")

    last_upload = db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).order_by(Resume.created_at.desc()).first()

    if last_upload and last_upload.created_at:
        time_since = datetime.now(timezone.utc) - last_upload.created_at.replace(tzinfo=timezone.utc)
        if time_since < timedelta(seconds=UPLOAD_COOLDOWN_SECONDS):
            wait = UPLOAD_COOLDOWN_SECONDS - int(time_since.total_seconds())
            raise HTTPException(status_code=429, detail=f"Please wait {wait}s before uploading again")

    pdf_bytes = await file.read()

    if len(pdf_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large, max 5MB")
    if not _looks_like_pdf(pdf_bytes):
        raise HTTPException(status_code=400, detail="Uploaded file does not look like a valid PDF")

    resume = Resume(
        user_id=current_user.id,
        file_name=file_name,
        pdf_data=pdf_bytes,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return ResumeUploadResponse(id=resume.id, file_name=resume.file_name, status="uploaded")


@router.post("/{resume_id}/parse", response_model=ResumeResponse)
async def parse_resume(
    resume_id: int = Path(..., ge=1, description="Resume ID to parse into structured application data."),
    payload: ParseRequest = ParseRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Parse a stored resume into normalized structured fields.

    Uses cloud AI, local AI, or rules-based parsing depending on the requested
    method. Results are validated and persisted back to the resume.

    Response codes:
    - 200: Parse succeeded and updated resume is returned.
    - 400: Unsupported parse method or OCR data missing.
    - 404: Resume not found for current user.
    - 429: Parse requested too soon after a previous parse.
    - 500: Internal parsing failure.
    - 502/504: Upstream parser timeout/failure represented by structured error.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.pdf_data:
        raise HTTPException(status_code=400, detail="Resume PDF data is required to parse")

    if resume.structured_data and resume.updated_at:
        time_since = datetime.now(timezone.utc) - resume.updated_at.replace(tzinfo=timezone.utc)
        if time_since < timedelta(seconds=10):
            raise HTTPException(status_code=429, detail="This resume was just parsed, wait a bit")

    method = normalize_parse_method(payload.method)
    if method is None:
        raise HTTPException(status_code=400, detail="Method must be one of: cloud, local, rules")

    input_payload = await get_parse_input_text(resume.pdf_data, method, resume=resume)
    if input_payload.get("ok") is False:
        raise HTTPException(
            status_code=int(input_payload.get("status_code") or 422),
            detail={
                "code": input_payload.get("error_code", "PARSE_INPUT_FAILED"),
                "message": input_payload.get("message", "Could not prepare parse input text."),
            },
        )

    parse_text = (input_payload.get("text") or "").strip()
    if not parse_text:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "PARSE_INPUT_EMPTY",
                "message": "Could not prepare parse input text.",
            },
        )

    _persist_parse_input_cache(
        resume,
        parse_text=parse_text,
        method=method,
        source=input_payload.get("source"),
    )
    db.commit()
    db.refresh(resume)

    parse_result = await parse_markdown_with_fallback(parse_text, method)

    if parse_result.get("ok") is False:
        error_code = parse_result.get("error_code", "PARSE_FAILED")
        message = parse_result.get("message", "Parsing failed")
        status = 504 if "TIMEOUT" in error_code else 502
        raise HTTPException(
            status_code=status,
            detail={"code": error_code, "message": message},
        )

    structured = parse_result.get("structured")
    effective_method = parse_result.get("effective_method") or method

    if structured is None:
        raise HTTPException(status_code=500, detail="Parsing failed")

    structured = validate_and_fix(structured)

    resume.structured_data = structured
    resume.parse_method = effective_method
    resume.portal_ready = structured.get("_validation", {}).get("portal_ready", False)
    _set_review_draft(resume, structured, status="pending")
    db.commit()
    db.refresh(resume)

    return resume


@router.get("/", response_model=list[ResumeListItem])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List resumes owned by the authenticated user.

    Returns newest-first metadata records suitable for dashboard lists and
    selection controls.

    Response codes:
    - 200: Resume list returned successfully (possibly empty).
    """
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).all()
    dirty = False
    for resume in resumes:
        dirty = _refresh_resume_validation_if_needed(resume) or dirty
    if dirty:
        db.commit()
    return resumes


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: int = Path(..., ge=1, description="Resume ID to retrieve."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a single resume record with parsing metadata.

    Returns resume details including structured fields, parser method, and
    readiness flags.

    Response codes:
    - 200: Resume returned successfully.
    - 404: Resume not found for current user.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if _refresh_resume_validation_if_needed(resume):
        db.commit()
        db.refresh(resume)
    return resume


@router.get("/{resume_id}/review-draft", response_model=ResumeReviewDraftResponse)
def get_review_draft(
    resume_id: int = Path(..., ge=1, description="Resume ID whose persisted review draft should be returned."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    review_draft = _current_review_draft(resume)
    if not review_draft:
        raise HTTPException(status_code=400, detail="Resume has not been parsed yet")

    return ResumeReviewDraftResponse(
        resume_id=resume.id,
        file_name=resume.file_name,
        parse_method=resume.parse_method,
        review_status=resume.review_status,
        review_updated_at=resume.review_updated_at,
        review_draft=review_draft,
        review_schema=REVIEW_DRAFT_SCHEMA,
    )


@router.put("/{resume_id}/review-draft", response_model=ResumeReviewDraftResponse)
def update_review_draft(
    payload: ResumeReviewDraftUpdate,
    resume_id: int = Path(..., ge=1, description="Resume ID whose review draft should be updated."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    current_review_draft = _current_review_draft(resume)
    if current_review_draft is None and not isinstance(resume.structured_data, dict):
        raise HTTPException(status_code=400, detail="Resume has not been parsed yet")

    _set_review_draft(resume, payload.review_draft, status="pending")
    db.commit()
    db.refresh(resume)

    return ResumeReviewDraftResponse(
        resume_id=resume.id,
        file_name=resume.file_name,
        parse_method=resume.parse_method,
        review_status=resume.review_status,
        review_updated_at=resume.review_updated_at,
        review_draft=_current_review_draft(resume) or {},
        review_schema=REVIEW_DRAFT_SCHEMA,
    )


@router.post("/{resume_id}/review-conflicts", response_model=ResumeReviewConflictResponse)
def review_conflicts(
    payload: ResumeReviewConflictRequest,
    resume_id: int = Path(..., ge=1, description="Resume ID whose reviewed data should be compared against a target applicant profile."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    profile = db.query(ApplicantProfile).filter(
        ApplicantProfile.id == payload.profile_id,
        ApplicantProfile.user_id == current_user.id,
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    sync_profile_storage(profile)
    reviewed_data = payload.reviewed_data or _current_review_draft(resume)
    if not isinstance(reviewed_data, dict):
        raise HTTPException(status_code=400, detail="Resume has no review draft")

    incoming_canonical = normalize_canonical_data(reviewed_data)
    existing_canonical = normalize_canonical_data(profile.canonical_data or {})
    conflicts = generate_review_conflicts(existing_canonical, incoming_canonical)

    return ResumeReviewConflictResponse(
        profile_id=profile.id,
        conflict_count=len(conflicts),
        conflicts=conflicts,
    )


@router.post("/{resume_id}/apply-review", response_model=ResumeReviewApplyResponse)
def apply_review(
    payload: ResumeReviewApplyRequest,
    resume_id: int = Path(..., ge=1, description="Resume ID whose reviewed draft should be applied to the applicant profile system."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    incoming_canonical = normalize_canonical_data(payload.reviewed_data)
    if payload.mode not in {"existing", "new"}:
        raise HTTPException(status_code=400, detail="Mode must be 'existing' or 'new'")

    profile: ApplicantProfile | None = None
    conflicts: list[dict] = []

    if payload.mode == "existing":
        if payload.profile_id is None:
            raise HTTPException(status_code=400, detail="profile_id is required when mode='existing'")
        profile = db.query(ApplicantProfile).filter(
            ApplicantProfile.id == payload.profile_id,
            ApplicantProfile.user_id == current_user.id,
        ).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        sync_profile_storage(profile)
        merged_canonical, conflicts = merge_review_into_profile(
            normalize_canonical_data(profile.canonical_data or {}),
            incoming_canonical,
            payload.conflict_resolutions or {},
        )
        profile.canonical_data = merged_canonical
        sync_profile_storage(profile)
    else:
        count = db.query(func.count(ApplicantProfile.id)).filter(
            ApplicantProfile.user_id == current_user.id
        ).scalar()
        if count >= MAX_PROFILES_PER_USER:
            raise HTTPException(status_code=429, detail=f"Max {MAX_PROFILES_PER_USER} applicant profiles allowed")

        suggested_name = (
            (payload.profile_name or "").strip()
            or " ".join(
                part for part in [
                    incoming_canonical.get("personal_info", {}).get("first_name"),
                    incoming_canonical.get("personal_info", {}).get("last_name"),
                ]
                if part
            )
            or os.path.splitext(resume.file_name)[0]
            or "Imported Profile"
        )
        profile = ApplicantProfile(
            user_id=current_user.id,
            name=suggested_name[:100],
            is_active=True,
        )
        db.add(profile)
        db.flush()
        build_profile_from_review(profile, incoming_canonical)

    db.query(ApplicantProfile).filter(
        ApplicantProfile.user_id == current_user.id,
        ApplicantProfile.id != profile.id,
    ).update({"is_active": False})
    profile.is_active = True

    _set_review_draft(resume, payload.reviewed_data, status="applied")
    db.commit()
    db.refresh(profile)
    db.refresh(resume)

    return ResumeReviewApplyResponse(
        resume_id=resume.id,
        profile_id=profile.id,
        review_status=resume.review_status or "applied",
        conflict_count=len(conflicts),
        profile=ProfileResponse.model_validate(profile).model_dump(),
    )


@router.get("/{resume_id}/pdf")
def get_resume_pdf(
    resume_id: int = Path(..., ge=1, description="Resume ID whose PDF binary should be streamed."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream the original uploaded resume PDF.

    Returns binary PDF content with an inline Content-Disposition header so
    browsers can preview the document.

    Response codes:
    - 200: PDF binary streamed successfully.
    - 404: Resume not found or PDF content unavailable.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    if not resume.pdf_data:
        raise HTTPException(status_code=404, detail="PDF file not available for this resume")
    return Response(
        content=resume.pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{resume.file_name}"'},
    )


@router.get("/{resume_id}/portal-check", response_model=PortalCheckResponse)
def portal_check(
    resume_id: int = Path(..., ge=1, description="Resume ID to evaluate for job portal readiness."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evaluate whether a parsed resume satisfies required portal fields.

    Computes readiness booleans and missing required field names based on
    normalized resume data.

    Response codes:
    - 200: Portal readiness computed successfully.
    - 400: Resume exists but has not been parsed yet.
    - 404: Resume not found for current user.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.structured_data:
        raise HTTPException(status_code=400, detail="Resume hasnt been parsed yet")

    ready, missing = check_portal_required(resume.structured_data)
    total = 15
    return PortalCheckResponse(
        portal_ready=ready,
        missing_fields=missing,
        total_required=total,
        filled_count=total - len(missing),
    )


@router.delete("/{resume_id}")
def delete_resume(
    resume_id: int = Path(..., ge=1, description="Resume ID to permanently delete."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a resume owned by the authenticated user.

    Removes the resume record and associated stored document data.

    Response codes:
    - 200: Resume deleted successfully.
    - 404: Resume not found for current user.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    db.delete(resume)
    db.commit()
    return {"message": "Resume deleted"}


# ── Async parse job endpoints ─────────────────────────────────────────────

def _run_parse_job(job_id: int):
    """Sync wrapper for async parse job runner used by FastAPI BackgroundTasks."""
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run_parse_job(job_id))
    except Exception as e:
        logger.exception("Parse job wrapper %d failed: %s", job_id, e)
    finally:
        loop.close()


@router.post("/{resume_id}/parse-async", response_model=ParseJobStartResponse, status_code=202)
async def start_async_parse(
    resume_id: int = Path(..., ge=1, description="Resume ID to parse asynchronously in a background job."),
    payload: ParseRequest = ParseRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Queue an asynchronous resume parsing job.

    Creates a parse job record, prevents duplicate active jobs for the same
    resume, and schedules the parser in FastAPI background tasks.

    Response codes:
    - 202: Parse job queued successfully.
    - 400: Resume lacks OCR data or method is invalid.
    - 404: Resume not found for current user.
    - 409: Another active parse job already exists for this resume.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.pdf_data:
        raise HTTPException(status_code=400, detail="Resume PDF data is required to parse")

    method = normalize_parse_method(payload.method)
    if method is None:
        raise HTTPException(status_code=400, detail="Method must be one of: cloud, local, rules")

    # Prevent duplicate active jobs for the same resume
    active = db.query(ParseJob).filter(
        ParseJob.resume_id == resume_id,
        ParseJob.user_id == current_user.id,
        ParseJob.status.in_(["queued", "parsing", "validating"]),
    ).first()
    if active:
        raise HTTPException(status_code=409, detail="A parse job is already running for this resume")

    job = ParseJob(
        resume_id=resume_id,
        user_id=current_user.id,
        method=method,
        status="queued",
        progress_stage="Queued…",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if settings.REDIS_ENABLED:
        queued = await enqueue_parse_job(job.id, resume_id, current_user.id, method)
        if not queued:
            background_tasks.add_task(_run_parse_job, job.id)
    else:
        background_tasks.add_task(_run_parse_job, job.id)

    return ParseJobStartResponse(job_id=job.id, status="queued")


@router.get("/queue/status")
async def get_queue_status(
    scope: str = Query(default="user", description="Queue scope: user or global."),
    focus_method: str | None = Query(default=None, description="Optional parse method focus for user queue position."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns queue status for current user with optional global details in development."""
    return await _build_queue_status_payload(
        db=db,
        current_user=current_user,
        scope=scope,
        focus_method=focus_method,
    )


@router.get("/parse-job/{job_id}", response_model=ParseJobResponse)
async def get_parse_job(
    job_id: int = Path(..., ge=1, description="Parse job ID to poll for status, progress, and results."),
    include_queue: bool = Query(default=False, description="Include a lightweight queue snapshot in the poll response."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Poll a parse job by ID.

    Returns current parse status, progress details, and summary/error metadata
    for asynchronous resume parsing.

    Response codes:
    - 200: Parse job returned successfully.
    - 404: Parse job not found for current user.
    """
    job = db.query(ParseJob).filter(ParseJob.id == job_id, ParseJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Parse job not found")

    response = ParseJobResponse.model_validate(job).model_dump()
    redis_status = await get_job_redis_status(job.id) if settings.REDIS_ENABLED else None

    attempt = None
    started_at = None
    completed_at = None
    if redis_status:
        try:
            attempt = int(redis_status.get("attempt")) if redis_status.get("attempt") is not None else None
        except Exception:
            attempt = None
        started_at = _parse_iso_datetime(redis_status.get("started_at"))
        completed_at = _parse_iso_datetime(redis_status.get("completed_at"))

    if job.status in ("success", "failed", "cancelled") and completed_at is None:
        completed_at = job.updated_at

    response["attempt"] = attempt
    response["started_at"] = started_at
    response["completed_at"] = completed_at
    response["elapsed_seconds"] = _compute_elapsed_seconds(job.created_at, started_at, completed_at)
    response["queue_position"] = None
    response["queue_total"] = None

    if include_queue:
        queue_snapshot = await _build_queue_status_payload(
            db=db,
            current_user=current_user,
            scope="user",
            focus_method=job.method,
        )
        response["queue_snapshot"] = queue_snapshot
        response["queue_position"] = queue_snapshot.get("current_user", {}).get("active_job_position")
        response["queue_total"] = queue_snapshot.get("current_user", {}).get("active_job_total")
    return response


@router.post("/parse-job/{job_id}/cancel")
def cancel_parse_job(
    job_id: int = Path(..., ge=1, description="Parse job ID to cancel if still in a non-terminal state."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel an in-progress parse job.

    Marks queued/parsing/validating jobs as cancelled. If the job is already in
    a terminal state, returns a no-op informational message.

    Response codes:
    - 200: Job cancelled or already terminal.
    - 404: Parse job not found for current user.
    """
    job = db.query(ParseJob).filter(ParseJob.id == job_id, ParseJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Parse job not found")

    if job.status in ("success", "failed", "cancelled"):
        return {"message": f"Job already in terminal state: {job.status}"}

    job.status = "cancelled"
    job.progress_stage = "Cancelled"
    db.commit()
    return {"message": "Parse job cancelled"}
