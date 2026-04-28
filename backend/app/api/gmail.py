import secrets
import base64
import hashlib
import html
import httpx
import re
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode
from app.db.session import get_db
from app.models.user import User
from app.models.user import GmailSuppression, GmailNotificationState, GmailFeedback
from app.models.apply_session import ApplySession, TrackedApplication
from app.api.deps import get_current_user, require_admin_or_developer
from app.core.rate_limit import enforce_subject_rate_limit
from app.core.config import settings
from app.services.gmail_scan import (
    ATS_DOMAIN_HINTS,
    ScanMessage,
    build_thread_signature,
    evaluate_message,
    normalize_company_key,
    normalize_subject_key,
    parse_sender_domain,
)
from urllib.parse import quote_plus

router = APIRouter(prefix="/api/integrations/gmail", tags=["gmail"])

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_SCOPES = "https://www.googleapis.com/auth/gmail.readonly"

SCAN_KEYWORDS = [
    "application", "interview", "offer", "unfortunately",
    "position", "we regret", "next steps", "congratulations",
    "candidacy", "hiring", "recruitment", "selected",
]
SCAN_RATE_LIMIT = 8
SCAN_RATE_WINDOW_SECONDS = 300


class GmailDebugMessage(BaseModel):
    subject: str = Field(default="")
    from_header: str = Field(default="", alias="from")
    date: str = Field(default="")
    snippet: str = Field(default="")
    body: str = Field(default="")

    class Config:
        populate_by_name = True


class GmailDebugScanRequest(BaseModel):
    messages: list[GmailDebugMessage] = Field(default_factory=list)
    require_ats: bool = True
    include_unsubmitted: bool = False


class GmailScanRequest(BaseModel):
    scan_mode: str = Field(default="new", max_length=24)
    query: str | None = Field(default=None, max_length=280)
    newer_than_days: int = Field(default=45, ge=1, le=36500)
    max_results: int = Field(default=20, ge=1, le=100)
    source_strictness: str = Field(default="hybrid_job_language", max_length=40)
    linkedin_mode: str = Field(default="linkedin_apply_only", max_length=40)


class GmailSuppressionCreateRequest(BaseModel):
    scope: str = Field(default="message")
    source_id: str | None = Field(default=None, max_length=255)
    from_header: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=255)
    company_hint: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=255)


class GmailNotificationStateCreateRequest(BaseModel):
    source_id: str = Field(default="", max_length=255)
    action: str = Field(default="snooze", max_length=40)


class GmailFeedbackCreateRequest(BaseModel):
    source_id: str | None = Field(default=None, max_length=255)
    from_header: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=255)
    company_hint: str | None = Field(default=None, max_length=120)
    triage_label: str = Field(default="unsure", max_length=40)
    override_status: str | None = Field(default=None, max_length=40)
    false_positive_reason: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=255)


def _get_fernet():
    key_material = (settings.GMAIL_TOKEN_ENCRYPTION_KEY or settings.SESSION_SECRET or "").strip()
    if not key_material:
        raise RuntimeError("Gmail token encryption key is not configured")
    derived_key = hashlib.sha256(key_material.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(derived_key))


def _encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode()).decode()


def _decrypt_token(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode()).decode()


def _clear_gmail_oauth_session(request: Request) -> None:
    request.session.pop("gmail_oauth_state", None)
    request.session.pop("gmail_oauth_user_id", None)


def _gmail_settings_redirect(service_state: str, reason: str | None = None) -> RedirectResponse:
    public_url = (settings.PUBLIC_APP_URL or "").rstrip("/")
    query = {"service": "gmail", "service_state": service_state}
    if reason:
        query["service_reason"] = reason
    return RedirectResponse(f"{public_url}/settings?{urlencode(query)}")


def _build_gmail_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.GMAIL_CLIENT_ID,
        "redirect_uri": settings.GMAIL_REDIRECT_URI,
        "response_type": "code",
        "scope": GMAIL_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{GOOGLE_AUTH_URL}?{query}"


def _start_gmail_connect(request: Request, current_user: User) -> str:
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_REDIRECT_URI:
        raise RuntimeError("not_configured")

    state = secrets.token_urlsafe(16)
    request.session["gmail_oauth_state"] = state
    request.session["gmail_oauth_user_id"] = current_user.id
    return _build_gmail_authorization_url(state)


@router.get("/connect")
async def gmail_connect(request: Request, current_user: User = Depends(get_current_user)):
    try:
        return RedirectResponse(_start_gmail_connect(request, current_user))
    except RuntimeError as exc:
        return _gmail_settings_redirect("error", str(exc) or "not_configured")


@router.post("/connect/start")
async def gmail_connect_start(request: Request, current_user: User = Depends(get_current_user)):
    try:
        return {"authorization_url": _start_gmail_connect(request, current_user)}
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc) or "not_configured")


@router.get("/callback")
async def gmail_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    expected_state = request.session.get("gmail_oauth_state")
    user_id = request.session.get("gmail_oauth_user_id")

    if not expected_state or state != expected_state or not user_id:
        _clear_gmail_oauth_session(request)
        return _gmail_settings_redirect("error", "invalid_state")

    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": settings.GMAIL_CLIENT_ID,
                "client_secret": settings.GMAIL_CLIENT_SECRET,
                "redirect_uri": settings.GMAIL_REDIRECT_URI,
                "grant_type": "authorization_code",
            })
            token_data = token_resp.json()
    except Exception:
        _clear_gmail_oauth_session(request)
        return _gmail_settings_redirect("error", "token_exchange_failed")

    refresh_token = token_data.get("refresh_token")
    access_token = token_data.get("access_token")

    if not refresh_token or not access_token:
        _clear_gmail_oauth_session(request)
        return _gmail_settings_redirect("error", "missing_tokens")

    try:
        async with httpx.AsyncClient() as client:
            profile = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            gmail_email = profile.json().get("email", "")
    except Exception:
        _clear_gmail_oauth_session(request)
        return _gmail_settings_redirect("error", "profile_fetch_failed")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        _clear_gmail_oauth_session(request)
        return _gmail_settings_redirect("error", "user_not_found")

    user.gmail_refresh_token = _encrypt_token(refresh_token)
    user.gmail_email = gmail_email
    db.commit()
    _clear_gmail_oauth_session(request)
    return _gmail_settings_redirect("connected")


@router.get("/status")
def gmail_status(current_user: User = Depends(get_current_user)):
    return {
        "connected": current_user.gmail_refresh_token is not None,
        "email": current_user.gmail_email,
    }


@router.delete("/disconnect")
async def gmail_disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.gmail_refresh_token:
        try:
            token = _decrypt_token(current_user.gmail_refresh_token)
            async with httpx.AsyncClient() as client:
                await client.post(GOOGLE_REVOKE_URL, params={"token": token})
        except Exception:
            pass

    current_user.gmail_refresh_token = None
    current_user.gmail_email = None
    db.commit()
    return {"message": "Gmail disconnected"}


async def _get_gmail_access_token(encrypted_refresh: str) -> str:
    refresh_token = _decrypt_token(encrypted_refresh)
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        data = resp.json()

    if data.get("error") == "invalid_grant":
        raise HTTPException(
            status_code=401,
            detail="Gmail token expired or revoked. Please reconnect your Gmail account."
        )

    token = data.get("access_token")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Could not refresh Gmail token. Please reconnect your Gmail account."
        )
    return token


def _allowed_apply_session_statuses(include_unsubmitted: bool) -> set[str]:
    if include_unsubmitted:
        return {"submitted", "in_progress", "started"}
    return {"submitted"}


def _normalize_scan_query(query: str | None) -> str:
    clean = " ".join(str(query or "").split())
    if not clean:
        return " OR ".join(SCAN_KEYWORDS)
    return clean[:280]


def _build_open_urls(*, source_id: str, from_header: str, subject: str, date: str) -> tuple[str, str]:
    direct = f"https://mail.google.com/mail/u/0/#inbox/{source_id}"
    sender_domain = parse_sender_domain(from_header)
    search_query = " ".join(
        part for part in [
            f"from:{sender_domain}" if sender_domain else "",
            f"subject:\"{subject}\"" if subject else "",
        ] if part
    ).strip()
    fallback = f"https://mail.google.com/mail/u/0/#search/{quote_plus(search_query or subject or from_header or source_id)}"
    return direct, fallback


def _should_fetch_full_body(*, from_header: str, subject: str, snippet: str) -> bool:
    domain = parse_sender_domain(from_header)
    combined = f"{domain} {(subject or '').lower()} {(snippet or '').lower()}"
    if any(hint in combined for hint in ATS_DOMAIN_HINTS):
        return True
    candidate_signals = (
        "application",
        "position",
        "interview",
        "candidate",
        "hiring",
        "offer",
        "recruit",
    )
    return any(signal in combined for signal in candidate_signals)


def _decode_gmail_body_data(encoded_data: str | None) -> str:
    if not encoded_data:
        return ""
    normalized = str(encoded_data).replace("-", "+").replace("_", "/")
    padding = "=" * ((4 - len(normalized) % 4) % 4)
    try:
        decoded = base64.b64decode(normalized + padding)
        return decoded.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_payload_text(payload: dict | None) -> str:
    if not isinstance(payload, dict):
        return ""
    chunks: list[str] = []

    mime_type = str(payload.get("mimeType") or "").lower()
    body_data = _decode_gmail_body_data((payload.get("body") or {}).get("data"))
    if body_data:
        if "html" in mime_type:
            body_data = re.sub(r"<[^>]+>", " ", body_data)
            body_data = html.unescape(body_data)
        chunks.append(body_data)

    for part in payload.get("parts") or []:
        part_text = _extract_payload_text(part)
        if part_text:
            chunks.append(part_text)

    return " ".join(chunks).strip()


def _suppression_matches(evaluated: dict, suppression: GmailSuppression) -> bool:
    scope = (suppression.scope or "").strip().lower()
    if scope == "message":
        source_id = str(evaluated.get("source_id") or "")
        return bool(source_id and suppression.source_id and source_id == suppression.source_id)
    if scope != "thread":
        return False
    sender_domain, subject_key, company_key = build_thread_signature(
        from_header=str(evaluated.get("from") or ""),
        subject=str(evaluated.get("subject") or ""),
        company_hint=evaluated.get("company_hint"),
    )
    return (
        (suppression.sender_domain or "") == sender_domain
        and (suppression.subject_key or "") == subject_key
        and (suppression.company_key or "") == company_key
    )


def _serialize_suppression(row: GmailSuppression) -> dict:
    return {
        "id": row.id,
        "scope": row.scope,
        "source_id": row.source_id,
        "sender_domain": row.sender_domain,
        "subject_key": row.subject_key,
        "company_key": row.company_key,
        "note": row.note,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _serialize_notification_state(row: GmailNotificationState) -> dict:
    return {
        "id": row.id,
        "source_id": row.source_id,
        "state": row.state,
        "snoozed_until": row.snoozed_until.isoformat() if row.snoozed_until else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _serialize_feedback(row: GmailFeedback) -> dict:
    return {
        "id": row.id,
        "source_id": row.source_id,
        "sender_domain": row.sender_domain,
        "subject_key": row.subject_key,
        "company_key": row.company_key,
        "triage_label": row.triage_label,
        "override_status": row.override_status,
        "false_positive_reason": row.false_positive_reason,
        "notes": row.notes,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _feedback_override_for_message(
    feedback_rows: list[GmailFeedback],
    *,
    source_id: str,
    sender_domain: str,
    subject_key: str,
    company_key: str,
) -> str | None:
    for row in feedback_rows:
        row_source_id = str(row.source_id or "").strip()
        if row_source_id and row_source_id == source_id:
            return str(row.override_status or "").strip().lower() or None
        if (
            (row.sender_domain or "") == sender_domain
            and (row.subject_key or "") == subject_key
            and (row.company_key or "") == company_key
        ):
            return str(row.override_status or "").strip().lower() or None
    return None


@router.get("/notification-states")
async def gmail_list_notification_states(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    rows = (
        db.query(GmailNotificationState)
        .filter(
            GmailNotificationState.user_id == current_user.id,
            (
                (GmailNotificationState.state == "dismissed")
                | (
                    (GmailNotificationState.state == "snoozed")
                    & (GmailNotificationState.snoozed_until > now)
                )
            ),
        )
        .order_by(GmailNotificationState.updated_at.desc(), GmailNotificationState.id.desc())
        .limit(400)
        .all()
    )
    return {"notification_states": [_serialize_notification_state(row) for row in rows]}


@router.post("/notification-states")
async def gmail_upsert_notification_state(
    payload: GmailNotificationStateCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    source_id = (payload.source_id or "").strip()
    if not source_id:
        raise HTTPException(status_code=400, detail="source_id is required")

    action = (payload.action or "").strip().lower()
    if action not in {"dismiss", "snooze"}:
        raise HTTPException(status_code=400, detail="action must be 'dismiss' or 'snooze'")

    row = (
        db.query(GmailNotificationState)
        .filter(
            GmailNotificationState.user_id == current_user.id,
            GmailNotificationState.source_id == source_id,
        )
        .first()
    )

    now = datetime.now(timezone.utc)
    if not row:
        row = GmailNotificationState(
            user_id=current_user.id,
            source_id=source_id,
        )
        db.add(row)

    if action == "dismiss":
        row.state = "dismissed"
        row.snoozed_until = None
    else:
        row.state = "snoozed"
        row.snoozed_until = now + timedelta(days=3)
    row.updated_at = now

    db.commit()
    db.refresh(row)
    return {"status": "ok", "notification_state": _serialize_notification_state(row)}


@router.delete("/notification-states/{source_id}")
async def gmail_delete_notification_state(
    source_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clean_source_id = (source_id or "").strip()
    if not clean_source_id:
        raise HTTPException(status_code=400, detail="source_id is required")

    row = (
        db.query(GmailNotificationState)
        .filter(
            GmailNotificationState.user_id == current_user.id,
            GmailNotificationState.source_id == clean_source_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Notification state not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "message": "Notification state removed"}


@router.get("/suppressions")
async def gmail_list_suppressions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(GmailSuppression)
        .filter(GmailSuppression.user_id == current_user.id)
        .order_by(GmailSuppression.created_at.desc(), GmailSuppression.id.desc())
        .limit(300)
        .all()
    )
    return {"suppressions": [_serialize_suppression(row) for row in rows]}


@router.get("/feedback")
async def gmail_list_feedback(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = (
        db.query(GmailFeedback)
        .filter(GmailFeedback.user_id == current_user.id)
        .order_by(GmailFeedback.created_at.desc(), GmailFeedback.id.desc())
        .limit(300)
        .all()
    )
    return {"feedback": [_serialize_feedback(row) for row in rows]}


@router.post("/feedback")
async def gmail_create_feedback(
    payload: GmailFeedbackCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    triage_label = (payload.triage_label or "").strip().lower()
    if triage_label not in {"relevant", "not_relevant", "unsure"}:
        raise HTTPException(status_code=400, detail="triage_label must be 'relevant', 'not_relevant', or 'unsure'")
    override_status = (payload.override_status or "").strip().lower() or None
    if override_status and override_status not in {"application_received", "interview_invite", "offer", "rejection", "unknown"}:
        raise HTTPException(status_code=400, detail="override_status is invalid")

    sender_domain, subject_key, company_key = build_thread_signature(
        from_header=(payload.from_header or ""),
        subject=(payload.subject or ""),
        company_hint=payload.company_hint,
    )
    source_id = (payload.source_id or "").strip() or None
    row = GmailFeedback(
        user_id=current_user.id,
        source_id=source_id,
        sender_domain=sender_domain or None,
        subject_key=subject_key or None,
        company_key=company_key or None,
        triage_label=triage_label,
        override_status=override_status,
        false_positive_reason=(payload.false_positive_reason or "").strip() or None,
        notes=(payload.notes or "").strip() or None,
    )
    db.add(row)

    suppression = None
    if triage_label == "not_relevant":
        if source_id:
            suppression = GmailSuppression(
                user_id=current_user.id,
                scope="message",
                source_id=source_id,
                note=(payload.false_positive_reason or "not_relevant feedback").strip()[:255],
            )
        elif sender_domain and subject_key:
            suppression = GmailSuppression(
                user_id=current_user.id,
                scope="thread",
                sender_domain=sender_domain,
                subject_key=subject_key,
                company_key=company_key,
                note=(payload.false_positive_reason or "not_relevant feedback").strip()[:255],
            )
        if suppression:
            db.add(suppression)

    db.commit()
    db.refresh(row)
    if suppression:
        db.refresh(suppression)
    return {
        "status": "ok",
        "feedback": _serialize_feedback(row),
        "suppression": _serialize_suppression(suppression) if suppression else None,
    }


@router.post("/suppressions")
async def gmail_create_suppression(
    payload: GmailSuppressionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope = (payload.scope or "message").strip().lower()
    if scope not in {"message", "thread"}:
        raise HTTPException(status_code=400, detail="scope must be 'message' or 'thread'")

    if scope == "message":
        source_id = (payload.source_id or "").strip()
        if not source_id:
            raise HTTPException(status_code=400, detail="source_id is required for message scope")
        row = GmailSuppression(
            user_id=current_user.id,
            scope="message",
            source_id=source_id,
            note=(payload.note or "").strip() or None,
        )
    else:
        sender_domain = parse_sender_domain(payload.from_header)
        subject_key = normalize_subject_key(payload.subject)
        company_key = normalize_company_key(payload.company_hint)
        if not sender_domain or not subject_key:
            raise HTTPException(status_code=400, detail="from_header and subject are required for thread scope")
        row = GmailSuppression(
            user_id=current_user.id,
            scope="thread",
            sender_domain=sender_domain,
            subject_key=subject_key,
            company_key=company_key,
            note=(payload.note or "").strip() or None,
        )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "ok", "suppression": _serialize_suppression(row)}


@router.delete("/suppressions/{suppression_id}")
async def gmail_delete_suppression(
    suppression_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(GmailSuppression)
        .filter(GmailSuppression.id == suppression_id, GmailSuppression.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Suppression not found")
    db.delete(row)
    db.commit()
    return {"status": "ok", "message": "Suppression removed"}


def _load_apply_session_scope(db: Session, user_id: int, *, include_unsubmitted: bool) -> list[dict]:
    allowed_statuses = _allowed_apply_session_statuses(include_unsubmitted)
    query = db.query(ApplySession).filter(ApplySession.user_id == user_id)
    if not include_unsubmitted:
        query = query.filter(ApplySession.status == "submitted")
    sessions = query.order_by(ApplySession.started_at.desc()).limit(200).all()
    return [
        {
            "id": row.id,
            "company": row.company,
            "job_title": row.job_title,
            "status": row.status,
        }
        for row in sessions
        if (row.status or "").strip().lower() in allowed_statuses
    ]


@router.post("/scan")
async def gmail_scan(
    payload: GmailScanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.gmail_refresh_token:
        raise HTTPException(status_code=400, detail="Gmail not connected")
    enforce_subject_rate_limit(
        "gmail:scan",
        current_user.id,
        limit=SCAN_RATE_LIMIT,
        window_seconds=SCAN_RATE_WINDOW_SECONDS,
    )

    scan_mode = (payload.scan_mode or "new").strip().lower()
    if scan_mode not in {"new", "saved"}:
        raise HTTPException(status_code=400, detail="scan_mode must be 'new' or 'saved'")
    source_strictness = (payload.source_strictness or "strict_career_domains").strip().lower()
    if source_strictness not in {"strict_career_domains", "hybrid_job_language"}:
        raise HTTPException(status_code=400, detail="source_strictness must be 'strict_career_domains' or 'hybrid_job_language'")
    linkedin_mode = (payload.linkedin_mode or "linkedin_apply_only").strip().lower()
    if linkedin_mode not in {"linkedin_apply_only", "linkedin_all_jobish", "linkedin_off"}:
        raise HTTPException(status_code=400, detail="linkedin_mode must be 'linkedin_apply_only', 'linkedin_all_jobish', or 'linkedin_off'")

    access_token = await _get_gmail_access_token(current_user.gmail_refresh_token)
    session_scope = _load_apply_session_scope(db, current_user.id, include_unsubmitted=False)
    allowed_statuses = _allowed_apply_session_statuses(False)

    query = _normalize_scan_query(payload.query)
    search_url = (
        "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        f"?q={query} newer_than:{int(payload.newer_than_days)}d&maxResults={int(payload.max_results)}"
    )
    suppressions = (
        db.query(GmailSuppression)
        .filter(GmailSuppression.user_id == current_user.id)
        .order_by(GmailSuppression.created_at.desc(), GmailSuppression.id.desc())
        .all()
    )
    feedback_rows = (
        db.query(GmailFeedback)
        .filter(
            GmailFeedback.user_id == current_user.id,
            (
                (GmailFeedback.triage_label == "not_relevant")
                | (GmailFeedback.override_status.isnot(None))
            ),
        )
        .order_by(GmailFeedback.created_at.desc(), GmailFeedback.id.desc())
        .all()
    )
    tracked_rows = (
        db.query(TrackedApplication)
        .filter(
            TrackedApplication.user_id == current_user.id,
            TrackedApplication.selection_state == "active",
        )
        .all()
    )
    tracked_by_source_ref = {str(row.source_ref or ""): row for row in tracked_rows if row.source_ref}
    tracked_by_thread_key = {str(row.thread_key or ""): row for row in tracked_rows if row.thread_key}

    async with httpx.AsyncClient() as client:
        resp = await client.get(search_url, headers={"Authorization": f"Bearer {access_token}"})
        if resp.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="Gmail token expired or revoked. Please reconnect your Gmail account."
            )
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Gmail API request failed")
        messages_data = resp.json()

        message_ids = [m["id"] for m in messages_data.get("messages", [])]
        included_results = []
        excluded_count = 0
        suppressed_message_hits = 0
        suppressed_chain_hits = 0
        suppression_miss_reasons: dict[str, int] = {"missing_source_id": 0, "missing_thread_signature": 0}
        tracked_updates_applied = 0
        excluded_by_noncareer_source = 0
        excluded_by_negative_intent = 0
        included_by_ats = 0
        included_by_linkedin_apply = 0
        feedback_applied_count = 0
        now = datetime.now(timezone.utc)

        for msg_id in message_ids[: int(payload.max_results)]:
            msg_resp = await client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if msg_resp.status_code != 200:
                continue

            msg = msg_resp.json()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            snippet = msg.get("snippet", "")
            subject = headers.get("Subject", "")
            from_header = headers.get("From", "")
            body_text = ""
            if _should_fetch_full_body(from_header=from_header, subject=subject, snippet=snippet):
                full_resp = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                    params={"format": "full"},
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if full_resp.status_code == 200:
                    full_msg = full_resp.json()
                    body_text = _extract_payload_text(full_msg.get("payload"))[:3000]

            evaluated = evaluate_message(
                ScanMessage(
                    subject=subject,
                    from_header=from_header,
                    date=headers.get("Date", ""),
                    snippet=snippet,
                    body=body_text,
                    source_id=msg_id,
                ),
                apply_sessions=session_scope,
                allowed_statuses=allowed_statuses,
                require_ats=True,
                source_strictness=source_strictness,
                linkedin_mode=linkedin_mode,
            )
            base_result = {
                "source_id": evaluated["source_id"],
                "subject": evaluated["subject"],
                "from": evaluated["from"],
                "date": evaluated["date"],
                "detected_status": evaluated["detected_status"],
                "manual_override_applied": False,
                "company_hint": evaluated["company_hint"],
                "snippet": evaluated["snippet"],
                "body_preview": evaluated.get("body_preview") or "",
                "ats_detected": evaluated["ats_detected"],
                "job_update_detected": evaluated.get("job_update_detected"),
                "source_bucket": evaluated.get("source_bucket"),
                "intent_score": evaluated.get("intent_score"),
                "matched_applied_job": evaluated["matched_applied_job"],
            }
            sender_domain, subject_key, company_key = build_thread_signature(
                from_header=evaluated["from"],
                subject=evaluated["subject"],
                company_hint=evaluated.get("company_hint"),
            )
            thread_key = f"{sender_domain}|{subject_key}|{company_key}"
            direct_url, fallback_url = _build_open_urls(
                source_id=str(evaluated["source_id"] or ""),
                from_header=evaluated["from"],
                subject=evaluated["subject"],
                date=evaluated["date"],
            )
            base_result = {
                **base_result,
                "sender_domain": sender_domain,
                "subject_key": subject_key,
                "company_key": company_key,
                "thread_key": thread_key,
                "gmail_open_url_direct": direct_url,
                "gmail_open_url_fallback": fallback_url,
            }
            source_id = str(evaluated.get("source_id") or "")
            tracked_match = tracked_by_source_ref.get(source_id) or tracked_by_thread_key.get(thread_key)
            if scan_mode == "saved" and not tracked_match:
                excluded_count += 1
                continue
            matched_suppression = next((row for row in suppressions if _suppression_matches(evaluated, row)), None)
            matched_feedback = next(
                (
                    row for row in feedback_rows
                    if (
                        (row.source_id and source_id == str(row.source_id))
                        or (
                            (row.sender_domain or "") == sender_domain
                            and (row.subject_key or "") == subject_key
                            and (row.company_key or "") == company_key
                        )
                    )
                ),
                None,
            )
            if matched_feedback:
                feedback_applied_count += 1
            suppress_from_feedback = bool(matched_feedback and (matched_feedback.triage_label or "").strip().lower() == "not_relevant")
            manual_override_status = _feedback_override_for_message(
                feedback_rows,
                source_id=source_id,
                sender_domain=sender_domain,
                subject_key=subject_key,
                company_key=company_key,
            )
            effective_status = manual_override_status or str(evaluated.get("detected_status") or "unknown")
            base_result["detected_status"] = effective_status
            base_result["manual_override_applied"] = bool(manual_override_status)
            if tracked_match:
                tracked_match.latest_status = effective_status
                tracked_match.last_update_at = now
                tracked_match.has_new_update = True
                tracked_updates_applied += 1
                base_result["tracked_id"] = tracked_match.id
                base_result["has_new_update"] = True
            else:
                base_result["tracked_id"] = None
                base_result["has_new_update"] = False
            if evaluated.get("include"):
                if matched_suppression or suppress_from_feedback:
                    suppression_scope = (matched_suppression.scope or "").lower() if matched_suppression else (
                        "message" if (matched_feedback and matched_feedback.source_id) else "thread"
                    )
                    if suppression_scope == "message":
                        suppressed_message_hits += 1
                        if not evaluated.get("source_id"):
                            suppression_miss_reasons["missing_source_id"] += 1
                    else:
                        suppressed_chain_hits += 1
                        if not sender_domain or not subject_key:
                            suppression_miss_reasons["missing_thread_signature"] += 1
                    excluded_count += 1
                    continue
                included_results.append({
                    **base_result,
                    "tracking_source": "gmail",
                    "confidence": "high",
                })
                if evaluated.get("ats_detected"):
                    included_by_ats += 1
                if evaluated.get("linkedin_apply_detected"):
                    included_by_linkedin_apply += 1
            else:
                if evaluated.get("exclude_reason") == "noncareer_source":
                    excluded_by_noncareer_source += 1
                if evaluated.get("exclude_reason") == "negative_intent":
                    excluded_by_negative_intent += 1
                excluded_count += 1

    if tracked_updates_applied > 0:
        db.commit()

    return {
        "gmail_email": current_user.gmail_email,
        "results_count": len(included_results),
        "matched_results_count": len(included_results),
        "results": included_results,
        "matched_results": included_results,
        "scan_scope": {
            "require_ats_or_job_update": True,
            "applied_job_statuses": sorted(allowed_statuses),
            "applied_job_candidates": len(session_scope),
            "excluded_count": excluded_count,
            "query": query,
            "scan_mode": scan_mode,
            "source_strictness": source_strictness,
            "linkedin_mode": linkedin_mode,
            "newer_than_days": int(payload.newer_than_days),
            "max_results": int(payload.max_results),
            "suppression_count": len(suppressions),
            "suppressed_message_hits": suppressed_message_hits,
            "suppressed_chain_hits": suppressed_chain_hits,
            "suppression_miss_reasons": suppression_miss_reasons,
            "tracked_updates_applied": tracked_updates_applied,
            "tracked_rows_seen": len(tracked_rows),
            "excluded_by_noncareer_source": excluded_by_noncareer_source,
            "excluded_by_negative_intent": excluded_by_negative_intent,
            "included_by_ats": included_by_ats,
            "included_by_linkedin_apply": included_by_linkedin_apply,
            "feedback_applied_count": feedback_applied_count,
        },
    }


@router.post("/debug/simulate-scan")
async def gmail_debug_simulate_scan(
    payload: GmailDebugScanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_developer),
):
    session_scope = _load_apply_session_scope(
        db,
        current_user.id,
        include_unsubmitted=payload.include_unsubmitted,
    )
    allowed_statuses = _allowed_apply_session_statuses(payload.include_unsubmitted)
    evaluated_messages = [
        evaluate_message(
            ScanMessage(
                subject=item.subject,
                from_header=item.from_header,
                date=item.date,
                snippet=item.snippet,
                source_id=f"dev-{idx}",
                body=item.body,
            ),
            apply_sessions=session_scope,
            allowed_statuses=allowed_statuses,
            require_ats=bool(payload.require_ats),
        )
        for idx, item in enumerate(payload.messages, start=1)
    ]
    included = [item for item in evaluated_messages if item.get("include")]
    return {
        "status": "ok",
        "require_ats": bool(payload.require_ats),
        "applied_job_statuses": sorted(allowed_statuses),
        "applied_job_candidates": len(session_scope),
        "submitted_messages": len(payload.messages),
        "included_count": len(included),
        "excluded_count": len(evaluated_messages) - len(included),
        "included_results": included,
        "all_evaluated": evaluated_messages,
    }
