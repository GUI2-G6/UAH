from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import enforce_ip_rate_limit, enforce_subject_rate_limit
from app.db.session import get_db
from app.models.beta_access_request import BetaAccessRequest
from app.schemas.beta_access import BetaAccessRequestCreate, BetaAccessRequestResponse
from app.services.email import EmailNotConfiguredError, send_email

router = APIRouter(prefix="/api/public", tags=["public"])
logger = logging.getLogger(__name__)

BETA_ACCESS_REQUEST_IP_LIMIT = 8
BETA_ACCESS_REQUEST_IP_WINDOW_SECONDS = 900
BETA_ACCESS_REQUEST_EMAIL_LIMIT = 3
BETA_ACCESS_REQUEST_EMAIL_WINDOW_SECONDS = 3600
DEFAULT_BETA_NOTIFY_EMAIL = "beta@uahapp.com"


def _build_notification_body(payload: BetaAccessRequestCreate, request: Request) -> str:
    submitted_from = payload.source_surface or "unknown"
    request_ip = request.client.host if request.client else "unknown"
    return (
        "New beta access request submitted.\n\n"
        f"Email: {payload.email}\n"
        f"Full name: {payload.full_name or 'Not provided'}\n"
        f"Source surface: {submitted_from}\n"
        f"Requester IP: {request_ip}\n\n"
        "Notes:\n"
        f"{payload.notes or 'Not provided'}\n"
    )


@router.post("/beta-access", response_model=BetaAccessRequestResponse)
def request_beta_access(
    payload: BetaAccessRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> BetaAccessRequestResponse:
    enforce_ip_rate_limit(
        "public:beta-access:create",
        request,
        limit=BETA_ACCESS_REQUEST_IP_LIMIT,
        window_seconds=BETA_ACCESS_REQUEST_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "public:beta-access:create:email",
        payload.email,
        limit=BETA_ACCESS_REQUEST_EMAIL_LIMIT,
        window_seconds=BETA_ACCESS_REQUEST_EMAIL_WINDOW_SECONDS,
    )

    db_request = BetaAccessRequest(
        email=payload.email,
        full_name=payload.full_name,
        notes=payload.notes,
        source_surface=payload.source_surface,
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    notify_target = (settings.BETA_ACCESS_NOTIFY_EMAIL or DEFAULT_BETA_NOTIFY_EMAIL).strip()
    if notify_target:
        try:
            send_email(
                to=notify_target,
                subject="UAH beta access request",
                text=_build_notification_body(payload, request),
            )
        except EmailNotConfiguredError as exc:
            logger.warning("beta_access_request email skipped because SMTP is not configured: %s", exc)
        except Exception:
            logger.exception("beta_access_request email send failed")

    return BetaAccessRequestResponse(message="Thanks - your beta access request has been received.")
