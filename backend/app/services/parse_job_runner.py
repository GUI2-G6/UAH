import logging

from app.db.session import SessionLocal
from app.models.parse_job import ParseJob
from app.models.resume import Resume
from app.services.resume_parser import normalize_parse_method, parse_markdown_by_method, validate_and_fix

logger = logging.getLogger(__name__)


async def run_parse_job(job_id: int) -> bool:
    """Run a parse job and persist state transitions to the database."""
    db = SessionLocal()
    try:
        job = db.query(ParseJob).filter(ParseJob.id == job_id).first()
        if not job or job.status == "cancelled":
            return True

        resume = db.query(Resume).filter(Resume.id == job.resume_id).first()
        if not resume or not resume.raw_markdown:
            job.status = "failed"
            job.error_code = "NO_DATA"
            job.error_message = "Resume has no OCR data to parse."
            db.commit()
            return False

        method = normalize_parse_method(job.method)
        if method is None:
            job.status = "failed"
            job.error_code = "PARSE_METHOD_INVALID"
            job.error_message = f"Unsupported parse method: {job.method}"
            db.commit()
            return False

        job.status = "parsing"
        stage_by_method = {
            "cloud": "Cloud AI parsing...",
            "local": "Local AI parsing...",
            "rules": "Rules-based parsing...",
        }
        job.progress_stage = stage_by_method.get(method, "Parsing...")
        db.commit()

        db.refresh(job)
        if job.status == "cancelled":
            return True

        structured = await parse_markdown_by_method(resume.raw_markdown, method)

        if isinstance(structured, dict) and structured.get("ok") is False:
            job.status = "failed"
            job.error_code = structured.get("error_code", "PARSE_FAILED")
            job.error_message = structured.get("message", "Parsing failed")
            db.commit()
            return False

        if structured is None:
            job.status = "failed"
            job.error_code = "PARSE_EMPTY"
            job.error_message = "Parsing produced no results."
            db.commit()
            return False

        db.refresh(job)
        if job.status == "cancelled":
            return True

        job.status = "validating"
        job.progress_stage = "Validating and fixing data..."
        db.commit()

        structured = validate_and_fix(structured)

        resume.structured_data = structured
        resume.parse_method = method
        resume.portal_ready = structured.get("_validation", {}).get("portal_ready", False)

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
        return True

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
        return False
    finally:
        db.close()
