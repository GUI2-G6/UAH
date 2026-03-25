from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.user import User
from app.models.resume import Resume
from app.api.deps import get_current_user
from app.schemas.resume import (
    ResumeUploadResponse, ResumeResponse, ResumeListItem,
    PortalCheckResponse, ParseRequest,
)
from app.services.resume_parser import (
    ocr_pdf, categorize_with_llm, parse_with_rules, validate_and_fix,
    check_portal_required,
)

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
        raise HTTPException(
            status_code=502,
            detail={
                "code": "OCR_EXTRACTION_FAILED",
                "message": "Could not extract text from the uploaded PDF.",
                "debug": {
                    "error_code": ocr_result.get("error_code"),
                    "status_code": ocr_result.get("status_code"),
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
