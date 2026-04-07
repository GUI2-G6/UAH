import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/api/integrations/gmail", tags=["gmail"])

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GMAIL_SCOPES = "https://www.googleapis.com/auth/gmail.readonly"

SCAN_KEYWORDS = [
    "application", "interview", "offer", "unfortunately",
    "position", "we regret", "next steps", "congratulations",
    "candidacy", "hiring", "recruitment", "selected",
]


@router.get("/connect")
async def gmail_connect(request: Request, current_user: User = Depends(get_current_user)):
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Gmail integration not configured")

    state = secrets.token_urlsafe(16)
    request.session["gmail_oauth_state"] = state
    request.session["gmail_oauth_user_id"] = current_user.id

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
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")


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
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code": code,
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "redirect_uri": settings.GMAIL_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        token_data = token_resp.json()

    refresh_token = token_data.get("refresh_token")
    access_token = token_data.get("access_token")

    if not refresh_token or not access_token:
        raise HTTPException(status_code=400, detail="Failed to get Gmail tokens")

    async with httpx.AsyncClient() as client:
        profile = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        gmail_email = profile.json().get("email", "")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.gmail_refresh_token = refresh_token
    user.gmail_email = gmail_email
    db.commit()

    public_url = (settings.PUBLIC_APP_URL or "").rstrip("/")
    return RedirectResponse(f"{public_url}/settings?gmail=connected")


@router.get("/status")
def gmail_status(current_user: User = Depends(get_current_user)):
    return {
        "connected": current_user.gmail_refresh_token is not None,
        "gmail_email": current_user.gmail_email,
    }


@router.delete("/disconnect")
def gmail_disconnect(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    current_user.gmail_refresh_token = None
    current_user.gmail_email = None
    db.commit()
    return {"message": "Gmail disconnected"}


async def _get_gmail_access_token(refresh_token: str) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(GOOGLE_TOKEN_URL, data={
            "client_id": settings.GMAIL_CLIENT_ID,
            "client_secret": settings.GMAIL_CLIENT_SECRET,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        data = resp.json()
    token = data.get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="Failed to refresh Gmail token")
    return token


@router.post("/scan")
async def gmail_scan(current_user: User = Depends(get_current_user)):
    if not current_user.gmail_refresh_token:
        raise HTTPException(status_code=400, detail="Gmail not connected")

    access_token = await _get_gmail_access_token(current_user.gmail_refresh_token)

    query = " OR ".join(SCAN_KEYWORDS)
    search_url = (
        "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        f"?q={query}&maxResults=20"
    )

    async with httpx.AsyncClient() as client:
        resp = await client.get(search_url, headers={"Authorization": f"Bearer {access_token}"})
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Gmail API request failed")
        messages_data = resp.json()

        message_ids = [m["id"] for m in messages_data.get("messages", [])]
        results = []

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

            status = "unknown"
            snippet_lower = snippet.lower()
            if any(w in snippet_lower for w in ["unfortunately", "regret", "not selected", "not moving forward"]):
                status = "rejection"
            elif any(w in snippet_lower for w in ["interview", "schedule", "meet", "next steps"]):
                status = "interview"
            elif any(w in snippet_lower for w in ["offer", "congratulations", "pleased to extend"]):
                status = "offer"

            results.append({
                "subject": headers.get("Subject", ""),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": snippet,
                "detected_status": status,
            })

    return {
        "gmail_email": current_user.gmail_email,
        "results_count": len(results),
        "results": results,
    }
