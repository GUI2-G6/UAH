from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import enforce_ip_rate_limit, enforce_subject_rate_limit
from app.db.session import get_db
from app.models.landing_feedback_submission import LandingFeedbackSubmission
from app.schemas.landing_feedback import LandingFeedbackCreate, LandingFeedbackResponse
from app.services.email import EmailNotConfiguredError, send_email

router = APIRouter(prefix="/api/public", tags=["public"])
logger = logging.getLogger(__name__)

LANDING_FEEDBACK_IP_LIMIT = 8
LANDING_FEEDBACK_IP_WINDOW_SECONDS = 900
LANDING_FEEDBACK_EMAIL_LIMIT = 3
LANDING_FEEDBACK_EMAIL_WINDOW_SECONDS = 3600
DEFAULT_LANDING_FEEDBACK_NOTIFY_EMAIL = "feedback@uahapp.com"


def _build_notification_body(payload: LandingFeedbackCreate, request: Request) -> str:
    submitted_from = payload.source_surface or "unknown"
    request_ip = request.client.host if request.client else "unknown"
    return (
        "New landing / wishlist feedback submission.\n\n"
        f"Email: {payload.email}\n"
        f"Name: {payload.full_name or 'Not provided'}\n"
        f"Source surface: {submitted_from}\n"
        f"Requester IP: {request_ip}\n\n"
        "What frustrates you most about your current job search?\n"
        f"{payload.frustration or 'Not provided'}\n\n"
        "What would you want in a job search and tracking tool?\n"
        f"{payload.features or 'Not provided'}\n\n"
        f"Notify when public access opens: {'Yes' if payload.notify_public else 'No'}\n"
        f"Interested in beta access: {'Yes' if payload.interested_beta else 'No'}\n"
    )


@router.post("/landing-feedback", response_model=LandingFeedbackResponse)
def submit_landing_feedback(
    payload: LandingFeedbackCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> LandingFeedbackResponse:
    enforce_ip_rate_limit(
        "public:landing-feedback:create",
        request,
        limit=LANDING_FEEDBACK_IP_LIMIT,
        window_seconds=LANDING_FEEDBACK_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "public:landing-feedback:create:email",
        payload.email,
        limit=LANDING_FEEDBACK_EMAIL_LIMIT,
        window_seconds=LANDING_FEEDBACK_EMAIL_WINDOW_SECONDS,
    )

    surface = (payload.source_surface or "landing_wishlist").strip() or "landing_wishlist"
    row = LandingFeedbackSubmission(
        email=payload.email,
        full_name=payload.full_name,
        frustration=payload.frustration,
        features=payload.features,
        notify_public=payload.notify_public,
        interested_beta=payload.interested_beta,
        source_surface=surface,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    notify_target = (
        settings.LANDING_FEEDBACK_NOTIFY_EMAIL or DEFAULT_LANDING_FEEDBACK_NOTIFY_EMAIL
    ).strip()
    if notify_target:
        try:
            send_email(
                to=notify_target,
                subject="UAH landing feedback",
                text=_build_notification_body(payload, request),
            )
        except EmailNotConfiguredError as exc:
            logger.warning("landing_feedback email skipped because SMTP is not configured: %s", exc)
        except Exception:
            logger.exception("landing_feedback email send failed")

    return LandingFeedbackResponse(message="Thanks — we received your feedback.")
