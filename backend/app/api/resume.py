import asyncio
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db, SessionLocal
from app.models.user import User
from app.models.resume import Resume
from app.models.parse_job import ParseJob
from app.api.deps import get_current_user
from app.schemas.resume import (
    ResumeUploadResponse, ResumeResponse, ResumeListItem,
    PortalCheckResponse, ParseRequest,
    ParseJobResponse, ParseJobStartResponse,
)
from app.services.resume_parser import (
    ocr_pdf, categorize_with_llm, parse_with_rules, validate_and_fix,
    check_portal_required,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resume", tags=["resume"])

MAX_RESUMES_PER_USER = 10
MAX_FILE_SIZE = 5 * 1024 * 1024
UPLOAD_COOLDOWN_SECONDS = 30


@router.post("/upload", response_model=ResumeUploadResponse, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

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

    ocr_result = await ocr_pdf(pdf_bytes)
    if not ocr_result.get("ok"):
        error_code = ocr_result.get("error_code") or "OCR_EXTRACTION_FAILED"
        status_code = int(ocr_result.get("status_code") or 502)
        public_message = "Could not extract text from the uploaded PDF."
        if error_code == "OCR_NOT_CONFIGURED":
            public_message = "Resume OCR service is not configured. Please contact support."
        elif error_code == "OCR_TIMEOUT":
            public_message = "Resume OCR request timed out. Please retry in a moment."

        raise HTTPException(
            status_code=status_code,
            detail={
                "code": "OCR_EXTRACTION_FAILED",
                "message": public_message,
                "debug": {
                    "error_code": error_code,
                    "status_code": status_code,
                    "exception_type": ocr_result.get("exception_type"),
                    "response_excerpt": ocr_result.get("response_excerpt"),
                },
            },
        )

    md_text = ocr_result.get("md_results", "")
    if not md_text:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "OCR_EMPTY_RESULTS",
                "message": "OCR completed but no text was detected in this PDF.",
            },
        )

    resume = Resume(
        user_id=current_user.id,
        file_name=file.filename,
        pdf_data=pdf_bytes,
        raw_markdown=md_text,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return ResumeUploadResponse(id=resume.id, file_name=resume.file_name, status="uploaded")


@router.post("/{resume_id}/parse", response_model=ResumeResponse)
async def parse_resume(
    resume_id: int,
    payload: ParseRequest = ParseRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.raw_markdown:
        raise HTTPException(status_code=400, detail="No OCR data to parse, upload the resume first")

    if resume.structured_data and resume.updated_at:
        time_since = datetime.now(timezone.utc) - resume.updated_at.replace(tzinfo=timezone.utc)
        if time_since < timedelta(seconds=10):
            raise HTTPException(status_code=429, detail="This resume was just parsed, wait a bit")

    if payload.method == "llm":
        structured = await categorize_with_llm(resume.raw_markdown)
    elif payload.method == "rules":
        structured = parse_with_rules(resume.raw_markdown)
    else:
        raise HTTPException(status_code=400, detail="Method must be 'llm' or 'rules'")

    if structured is None:
        raise HTTPException(status_code=500, detail="Parsing failed")

    # Handle structured error returns from parser functions
    if isinstance(structured, dict) and structured.get("ok") is False:
        error_code = structured.get("error_code", "PARSE_FAILED")
        message = structured.get("message", "Parsing failed")
        status = 504 if "TIMEOUT" in error_code else 502
        raise HTTPException(
            status_code=status,
            detail={"code": error_code, "message": message},
        )

    structured = validate_and_fix(structured)

    resume.structured_data = structured
    resume.parse_method = payload.method
    resume.portal_ready = structured.get("_validation", {}).get("portal_ready", False)
    db.commit()
    db.refresh(resume)

    return resume


@router.get("/", response_model=list[ResumeListItem])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).all()
    return resumes


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


@router.get("/{resume_id}/pdf")
def get_resume_pdf(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    db.delete(resume)
    db.commit()
    return {"message": "Resume deleted"}


# ── Async parse job endpoints ─────────────────────────────────────────────

def _run_parse_job(job_id: int):
    """Background task: run parse, update job status in DB."""
    db = SessionLocal()
    try:
        job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
        if not job or job.status == "cancelled":
            return

        resume = db.query(Resume).filter(Resume.id == job.resume_id).first()
        if not resume or not resume.raw_markdown:
            job.status = "failed"
            job.error_code = "NO_DATA"
            job.error_message = "Resume has no OCR data to parse."
            db.commit()
            return

        # Stage: parsing
        job.status = "parsing"
        job.progress_stage = "AI parsing…" if job.method == "llm" else "Rules-based parsing…"
        db.commit()

        # Check if cancelled before the expensive call
        db.refresh(job)
        if job.status == "cancelled":
            return

        # Run the actual parse (synchronous wrapper for async functions)
        loop = asyncio.new_event_loop()
        try:
            if job.method == "llm":
                structured = loop.run_until_complete(categorize_with_llm(resume.raw_markdown))
            else:
                structured = parse_with_rules(resume.raw_markdown)
        finally:
            loop.close()

        # Check for errors from parser
        if isinstance(structured, dict) and structured.get("ok") is False:
            job.status = "failed"
            job.error_code = structured.get("error_code", "PARSE_FAILED")
            job.error_message = structured.get("message", "Parsing failed")
            db.commit()
            return

        if structured is None:
            job.status = "failed"
            job.error_code = "PARSE_EMPTY"
            job.error_message = "Parsing produced no results."
            db.commit()
            return

        # Check cancelled again
        db.refresh(job)
        if job.status == "cancelled":
            return

        # Stage: validating
        job.status = "validating"
        job.progress_stage = "Validating and fixing data…"
        db.commit()

        structured = validate_and_fix(structured)

        # Save to resume
        resume.structured_data = structured
        resume.parse_method = job.method
        resume.portal_ready = structured.get("_validation", {}).get("portal_ready", False)

        # Build result summary for polling
        validation = structured.get("_validation", {})
        job.status = "success"
        job.progress_stage = "Complete"
        job.result_summary = {
            "portal_ready": validation.get("portal_ready", False),
            "has_name": validation.get("has_name", False),
            "has_email": validation.get("has_email", False),
            "education_count": validation.get("education_count", 0),
            "experience_count": validation.get("experience_count", 0),
            "skills_count": validation.get("skills_count", 0),
            "missing_count": len(validation.get("missing_required", [])),
        }
        db.commit()

    except Exception as e:
        logger.exception("Parse job %d failed: %s", job_id, e)
        try:
            job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
            if job and job.status not in ("cancelled", "success"):
                job.status = "failed"
                job.error_code = "INTERNAL_ERROR"
                job.error_message = "An unexpected error occurred during parsing."
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("/{resume_id}/parse-async", response_model=ParseJobStartResponse, status_code=202)
def start_async_parse(
    resume_id: int,
    payload: ParseRequest = ParseRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    if not resume.raw_markdown:
        raise HTTPException(status_code=400, detail="No OCR data to parse, upload the resume first")

    if payload.method not in ("llm", "rules"):
        raise HTTPException(status_code=400, detail="Method must be 'llm' or 'rules'")

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
        method=payload.method,
        status="queued",
        progress_stage="Queued…",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_run_parse_job, job.id)

    return ParseJobStartResponse(job_id=job.id, status="queued")


@router.get("/parse-job/{job_id}", response_model=ParseJobResponse)
def get_parse_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(ParseJob).filter(ParseJob.id == job_id, ParseJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Parse job not found")
    return job


@router.post("/parse-job/{job_id}/cancel")
def cancel_parse_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = db.query(ParseJob).filter(ParseJob.id == job_id, ParseJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Parse job not found")

    if job.status in ("success", "failed", "cancelled"):
        return {"message": f"Job already in terminal state: {job.status}"}

    job.status = "cancelled"
    job.progress_stage = "Cancelled"
    db.commit()
    return {"message": "Parse job cancelled"}
