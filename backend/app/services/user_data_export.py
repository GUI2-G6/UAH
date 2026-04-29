from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy.orm import Session

from app.models.applicant_profile import ApplicantProfile
from app.models.apply_session import ApplySession, ApplySessionEvent, TrackedApplication
from app.models.parse_job import ParseJob
from app.models.resume import Resume
from app.models.user import GmailFeedback, GmailNotificationState, GmailSuppression, SavedJob, User


def _to_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
    return str(value)


def _write_csv(rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _to_cell(row.get(key)) for key in fieldnames})
    return out.getvalue().encode("utf-8")


def build_user_data_export_zip(db: Session, user: User) -> bytes:
    user_id = int(user.id)
    resumes = db.query(Resume).filter(Resume.user_id == user_id).order_by(Resume.id.asc()).all()
    parse_jobs = db.query(ParseJob).filter(ParseJob.user_id == user_id).order_by(ParseJob.id.asc()).all()
    profiles = db.query(ApplicantProfile).filter(ApplicantProfile.user_id == user_id).order_by(ApplicantProfile.id.asc()).all()
    saved_jobs = db.query(SavedJob).filter(SavedJob.user_id == user_id).order_by(SavedJob.id.asc()).all()
    sessions = db.query(ApplySession).filter(ApplySession.user_id == user_id).order_by(ApplySession.id.asc()).all()
    tracked = db.query(TrackedApplication).filter(TrackedApplication.user_id == user_id).order_by(TrackedApplication.id.asc()).all()
    suppressions = db.query(GmailSuppression).filter(GmailSuppression.user_id == user_id).order_by(GmailSuppression.id.asc()).all()
    notification_states = db.query(GmailNotificationState).filter(GmailNotificationState.user_id == user_id).order_by(GmailNotificationState.id.asc()).all()
    feedback_rows = db.query(GmailFeedback).filter(GmailFeedback.user_id == user_id).order_by(GmailFeedback.id.asc()).all()

    session_ids = [int(row.id) for row in sessions]
    events = []
    if session_ids:
        events = (
            db.query(ApplySessionEvent)
            .filter(ApplySessionEvent.session_id.in_(session_ids))
            .order_by(ApplySessionEvent.id.asc())
            .all()
        )

    files: dict[str, bytes] = {}
    files["account_profile.csv"] = _write_csv(
        [{
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email_verified": user.email_verified,
            "is_active": user.is_active,
            "is_developer": user.is_developer,
            "google_id": user.google_id,
            "gmail_email": user.gmail_email,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }],
        [
            "id", "email", "username", "first_name", "last_name", "email_verified", "is_active",
            "is_developer", "google_id", "gmail_email", "created_at", "updated_at",
        ],
    )
    files["resumes.csv"] = _write_csv(
        [{
            "id": row.id,
            "file_name": row.file_name,
            "has_pdf": row.has_pdf,
            "raw_markdown": row.raw_markdown,
            "raw_markdown_source": row.raw_markdown_source,
            "raw_markdown_method": row.raw_markdown_method,
            "raw_markdown_updated_at": row.raw_markdown_updated_at,
            "structured_data": row.structured_data,
            "portal_ready": row.portal_ready,
            "parse_method": row.parse_method,
            "review_status": row.review_status,
            "review_draft": row.review_draft,
            "review_updated_at": row.review_updated_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        } for row in resumes],
        [
            "id", "file_name", "has_pdf", "raw_markdown", "raw_markdown_source", "raw_markdown_method",
            "raw_markdown_updated_at", "structured_data", "portal_ready", "parse_method", "review_status",
            "review_draft", "review_updated_at", "created_at", "updated_at",
        ],
    )
    files["parse_jobs.csv"] = _write_csv(
        [{
            "id": row.id,
            "resume_id": row.resume_id,
            "method": row.method,
            "status": row.status,
            "progress_stage": row.progress_stage,
            "error_code": row.error_code,
            "error_message": row.error_message,
            "result_summary": row.result_summary,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        } for row in parse_jobs],
        ["id", "resume_id", "method", "status", "progress_stage", "error_code", "error_message", "result_summary", "created_at", "updated_at"],
    )
    files["applicant_profiles.csv"] = _write_csv(
        [row.__dict__ for row in profiles],
        [
            "id", "name", "is_active", "first_name", "middle_name", "last_name", "full_legal_name", "preferred_name",
            "suffix", "email", "phone", "linkedin", "portfolio", "street_address", "city", "state", "zip",
            "summary", "work_auth", "requires_sponsorship", "degree", "major", "university", "grad_year", "gpa",
            "years_experience", "job_title", "skills_text", "certifications_text", "professional_links_text",
            "education_history_text", "employment_history_text", "canonical_data", "token_map", "demographic_gender",
            "demographic_ethnicity", "veteran_status", "disability_status", "california_resident", "created_at", "updated_at",
        ],
    )
    files["saved_jobs.csv"] = _write_csv(
        [row.__dict__ for row in saved_jobs],
        ["id", "job_id", "provider", "provider_job_id", "title", "company", "url", "created_at"],
    )
    files["apply_sessions.csv"] = _write_csv(
        [row.__dict__ for row in sessions],
        ["id", "job_id", "job_title", "company", "ats_url", "job_url", "status", "platform", "resume_id", "fields_matched", "fields_filled", "notes", "started_at", "updated_at", "finalized_at"],
    )
    files["apply_session_events.csv"] = _write_csv(
        [row.__dict__ for row in events],
        ["id", "session_id", "event_type", "payload", "created_at"],
    )
    files["tracked_applications.csv"] = _write_csv(
        [{
            "id": row.id,
            "apply_session_id": row.apply_session_id,
            "source_type": row.source_type,
            "source_ref": row.source_ref,
            "thread_key": row.thread_key,
            "company": row.company,
            "job_title": row.job_title,
            "latest_status": row.latest_status,
            "selection_state": row.selection_state,
            "has_new_update": row.has_new_update,
            "last_update_at": row.last_update_at,
            "last_seen_at": row.last_seen_at,
            "metadata_json": row.metadata_json,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        } for row in tracked],
        ["id", "apply_session_id", "source_type", "source_ref", "thread_key", "company", "job_title", "latest_status", "selection_state", "has_new_update", "last_update_at", "last_seen_at", "metadata_json", "created_at", "updated_at"],
    )
    files["gmail_suppressions.csv"] = _write_csv(
        [row.__dict__ for row in suppressions],
        ["id", "scope", "source_id", "sender_domain", "subject_key", "company_key", "note", "created_at"],
    )
    files["gmail_notification_states.csv"] = _write_csv(
        [row.__dict__ for row in notification_states],
        ["id", "source_id", "state", "snoozed_until", "created_at", "updated_at"],
    )
    files["gmail_feedback.csv"] = _write_csv(
        [row.__dict__ for row in feedback_rows],
        ["id", "source_id", "sender_domain", "subject_key", "company_key", "triage_label", "override_status", "false_positive_reason", "notes", "created_at"],
    )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    return zip_buffer.getvalue()

