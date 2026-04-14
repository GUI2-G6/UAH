import logging
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.parse_job import ParseJob
from app.models.resume import Resume
from app.services.resume_parser import (
    normalize_parse_method,
    parse_markdown_by_method,
    validate_and_fix,
    get_parse_input_text,
)

logger = logging.getLogger(__name__)


def _fail_job(job: ParseJob, code: str, message: str) -> None:
    job.status = "failed"
    job.error_code = code
    job.error_message = message


async def run_parse_job(job_id: int) -> bool:
    """Run a parse job and persist state transitions to the database."""
    db = SessionLocal()
    try:
        job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
        if not job or job.status == "cancelled":
            return True

        conflicting = db.query(ParseJob).filter(
            ParseJob.resume_id == job.resume_id,
            ParseJob.id != job.id,
            ParseJob.status.in_(["parsing", "validating"]),
        ).first()
        if conflicting:
            _fail_job(
                job,
                "CONCURRENT_RESUME_PARSE",
                "Another parse job is already processing this resume.",
            )
            db.commit()
            return False

        resume_query = db.query(Resume).filter(Resume.id == job.resume_id)
        try:
            resume = resume_query.with_for_update(nowait=True).first()
        except Exception:
            resume = resume_query.first()

        if not resume or not resume.pdf_data:
            _fail_job(job, "NO_DATA", "Resume PDF is not available for parsing.")
            db.commit()
            return False

        if int(resume.user_id) != int(job.user_id):
            _fail_job(
                job,
                "RESUME_OWNERSHIP_MISMATCH",
                "Parse job user ownership does not match the resume owner.",
            )
            db.commit()
            return False

        method = normalize_parse_method(job.method)
        if method is None:
            _fail_job(job, "PARSE_METHOD_INVALID", f"Unsupported parse method: {job.method}")
            db.commit()
            return False

        job.status = "parsing"
        stage_by_method = {
            "cloud": "Cloud OCR + parsing...",
            "local": "Local OCR + parsing...",
            "rules": "Rules parsing from embedded text...",
        }
        job.progress_stage = stage_by_method.get(method, "Parsing...")
        db.commit()

        db.refresh(job)
        if job.status == "cancelled":
            return True

        job.progress_stage = "Preparing parse input..."
        db.commit()

        input_payload = await get_parse_input_text(resume.pdf_data, method)
        if input_payload.get("ok") is False:
            _fail_job(
                job,
                input_payload.get("error_code", "PARSE_INPUT_FAILED"),
                input_payload.get("message", "Could not prepare parse input text."),
            )
            db.commit()
            return False

        parse_text = input_payload.get("text") or ""
        if not parse_text:
            _fail_job(job, "PARSE_INPUT_EMPTY", "Could not prepare parse input text.")
            db.commit()
            return False

        db.refresh(job)
        if job.status == "cancelled":
            return True

        job.progress_stage = "Running parser..."
        db.commit()

        structured = await parse_markdown_by_method(parse_text, method)

        if isinstance(structured, dict) and structured.get("ok") is False:
            _fail_job(
                job,
                structured.get("error_code", "PARSE_FAILED"),
                structured.get("message", "Parsing failed"),
            )
            db.commit()
            return False

        if structured is None:
            _fail_job(job, "PARSE_EMPTY", "Parsing produced no results.")
            db.commit()
            return False

        db.refresh(job)
        if job.status == "cancelled":
            return True

        job.status = "validating"
        job.progress_stage = "Validating and fixing data..."
        db.commit()

        structured = validate_and_fix(structured)

        resume.raw_markdown = parse_text
        resume.structured_data = structured
        resume.parse_method = method
        resume.portal_ready = structured.get("_validation", {}).get("portal_ready", False)
        resume.review_status = "pending"
        resume.review_draft = structured
        resume.review_updated_at = datetime.now(timezone.utc)

        validation = structured.get("_validation", {})
        job.status = "success"
        job.progress_stage = "Complete"
        job.error_code = None
        job.error_message = None
        job.result_summary = {
            "portal_ready": validation.get("portal_ready", False),
            "has_name": validation.get("has_name", False),
            "has_email": validation.get("has_email", False),
            "education_count": validation.get("education_count", 0),
            "experience_count": validation.get("experience_count", 0),
            "skills_count": validation.get("skills_count", 0),
            "missing_count": len(validation.get("missing_required", [])),
            "missing_required": validation.get("missing_required", []),
        }
        db.commit()
        return True

    except Exception as e:
        logger.exception("Parse job %d failed: %s", job_id, e)
        try:
            job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
            if job and job.status not in ("cancelled", "success"):
                _fail_job(job, "INTERNAL_ERROR", "An unexpected error occurred during parsing.")
                db.commit()
        except Exception:
            pass
        return False
    finally:
        db.close()
