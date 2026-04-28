import secrets
import base64
import hashlib
import httpx
from pydantic import BaseModel, Field
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode
from app.db.session import get_db
from app.models.user import User
from app.models.apply_session import ApplySession
from app.api.deps import get_current_user, require_admin_or_developer
from app.core.rate_limit import enforce_subject_rate_limit
from app.core.config import settings
from app.services.gmail_scan import ScanMessage, evaluate_message

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

    class Config:
        populate_by_name = True


class GmailDebugScanRequest(BaseModel):
    messages: list[GmailDebugMessage] = Field(default_factory=list)
    require_ats: bool = True
    include_unsubmitted: bool = False


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

    access_token = await _get_gmail_access_token(current_user.gmail_refresh_token)
    session_scope = _load_apply_session_scope(db, current_user.id, include_unsubmitted=False)
    allowed_statuses = _allowed_apply_session_statuses(False)

    query = " OR ".join(SCAN_KEYWORDS)
    search_url = (
        "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        f"?q={query}&maxResults=20"
    )

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
        provisional_results = []
        excluded_count = 0

        for msg_id in message_ids[:20]:
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

            evaluated = evaluate_message(
                ScanMessage(
                    subject=subject,
                    from_header=from_header,
                    date=headers.get("Date", ""),
                    snippet=snippet,
                    source_id=msg_id,
                ),
                apply_sessions=session_scope,
                allowed_statuses=allowed_statuses,
                require_ats=True,
            )
            base_result = {
                "subject": evaluated["subject"],
                "from": evaluated["from"],
                "date": evaluated["date"],
                "detected_status": evaluated["detected_status"],
                "company_hint": evaluated["company_hint"],
                "snippet": evaluated["snippet"],
                "ats_detected": evaluated["ats_detected"],
                "matched_applied_job": evaluated["matched_applied_job"],
            }
            if evaluated.get("include"):
                included_results.append({
                    **base_result,
                    "tracking_source": "matched",
                    "confidence": "high",
                })
            elif evaluated.get("ats_detected"):
                provisional_results.append({
                    **base_result,
                    "tracking_source": "gmail_provisional",
                    "confidence": "medium",
                    "exclude_reason": evaluated.get("exclude_reason"),
                })
            else:
                excluded_count += 1

    return {
        "gmail_email": current_user.gmail_email,
        "results_count": len(included_results),
        "matched_results_count": len(included_results),
        "provisional_results_count": len(provisional_results),
        "results": included_results,
        "matched_results": included_results,
        "provisional_results": provisional_results,
        "scan_scope": {
            "require_ats_sender": True,
            "applied_job_statuses": sorted(allowed_statuses),
            "applied_job_candidates": len(session_scope),
            "excluded_count": excluded_count,
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
