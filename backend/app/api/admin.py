"""Admin-only invite management endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user
from app.core.rate_limit import (
    enforce_ip_rate_limit,
    enforce_subject_rate_limit,
    get_request_client_ip,
)
from app.db.session import get_db
from app.models.invite import Invite
from app.models.user import User
from app.schemas.invite import InviteBatchCreate, InviteCreate, InviteResponse

router = APIRouter(tags=["admin"])
logger = logging.getLogger(__name__)

INVITE_CREATE_IP_LIMIT = 20
INVITE_CREATE_IP_WINDOW_SECONDS = 900
INVITE_CREATE_ADMIN_LIMIT = 15
INVITE_CREATE_ADMIN_WINDOW_SECONDS = 900
INVITE_REVOKE_IP_LIMIT = 40
INVITE_REVOKE_IP_WINDOW_SECONDS = 900
INVITE_REVOKE_ADMIN_LIMIT = 30
INVITE_REVOKE_ADMIN_WINDOW_SECONDS = 900


def _normalize_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _invite_fingerprint(code: str) -> str:
    normalized = str(code or "").strip()
    if not normalized:
        return "unknown"
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]
    return f"{normalized[:6]}...:{digest}"


def _audit_invite_event(
    *,
    action: str,
    actor_id: int,
    request: Request,
    invite_count: int = 0,
    fingerprints: list[str] | None = None,
    outcome: str = "success",
) -> None:
    logger.info(
        "invite_admin action=%s actor_id=%s ip=%s count=%s outcome=%s codes=%s",
        action,
        actor_id,
        get_request_client_ip(request),
        invite_count,
        outcome,
        ",".join(fingerprints or []),
    )


def _generate_unique_invite_code(db: Session, reserved_codes: set[str] | None = None) -> str:
    reserved = reserved_codes or set()

    while True:
        code = secrets.token_urlsafe(24)
        if code in reserved:
            continue
        existing = db.query(Invite.id).filter(Invite.code == code).first()
        if not existing:
            return code


def _build_invites(
    *,
    db: Session,
    current_user: User,
    count: int,
    expires_at: datetime | None,
) -> list[Invite]:
    normalized_expires_at = _normalize_utc_datetime(expires_at)
    reserved_codes: set[str] = set()
    invites: list[Invite] = []

    for _ in range(count):
        code = _generate_unique_invite_code(db, reserved_codes=reserved_codes)
        reserved_codes.add(code)
        invites.append(
            Invite(
                code=code,
                created_by=current_user.id,
                expires_at=normalized_expires_at,
                is_active=True,
            )
        )

    db.add_all(invites)
    db.commit()
    for invite in invites:
        db.refresh(invite)
    return invites


@router.post("/invites", response_model=InviteResponse)
def create_invite(
    payload: InviteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Generate a single invite code for the invite-only beta."""
    enforce_ip_rate_limit(
        "admin:invites:create",
        request,
        limit=INVITE_CREATE_IP_LIMIT,
        window_seconds=INVITE_CREATE_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "admin:invites:create:admin",
        current_user.id,
        limit=INVITE_CREATE_ADMIN_LIMIT,
        window_seconds=INVITE_CREATE_ADMIN_WINDOW_SECONDS,
    )

    invites = _build_invites(
        db=db,
        current_user=current_user,
        count=1,
        expires_at=payload.expires_at,
    )
    _audit_invite_event(
        action="create_single",
        actor_id=int(current_user.id),
        request=request,
        invite_count=1,
        fingerprints=[_invite_fingerprint(invites[0].code)],
    )
    return invites[0]


@router.post("/invites/batch", response_model=list[InviteResponse])
def create_invites_batch(
    payload: InviteBatchCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Generate multiple invite codes in one request."""
    enforce_ip_rate_limit(
        "admin:invites:create",
        request,
        limit=INVITE_CREATE_IP_LIMIT,
        window_seconds=INVITE_CREATE_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "admin:invites:create:admin",
        current_user.id,
        limit=INVITE_CREATE_ADMIN_LIMIT,
        window_seconds=INVITE_CREATE_ADMIN_WINDOW_SECONDS,
    )

    invites = _build_invites(
        db=db,
        current_user=current_user,
        count=payload.count,
        expires_at=payload.expires_at,
    )
    _audit_invite_event(
        action="create_batch",
        actor_id=int(current_user.id),
        request=request,
        invite_count=len(invites),
        fingerprints=[_invite_fingerprint(invite.code) for invite in invites[:10]],
    )
    return invites


@router.get("/invites", response_model=list[InviteResponse])
def list_invites(
    used: bool | None = Query(default=None),
    active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """List invite codes with optional used/active filters."""
    query = db.query(Invite)

    if used is not None:
        if used:
            query = query.filter(Invite.used_by.is_not(None))
        else:
            query = query.filter(Invite.used_by.is_(None))

    if active is not None:
        query = query.filter(Invite.is_active.is_(active))

    return query.order_by(Invite.created_at.desc(), Invite.id.desc()).all()


@router.delete("/invites/{code}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(
    code: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Soft-revoke an invite code while keeping the audit trail intact."""
    enforce_ip_rate_limit(
        "admin:invites:revoke",
        request,
        limit=INVITE_REVOKE_IP_LIMIT,
        window_seconds=INVITE_REVOKE_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "admin:invites:revoke:admin",
        current_user.id,
        limit=INVITE_REVOKE_ADMIN_LIMIT,
        window_seconds=INVITE_REVOKE_ADMIN_WINDOW_SECONDS,
    )

    invite = db.query(Invite).filter(Invite.code == code).first()
    if not invite:
        _audit_invite_event(
            action="revoke",
            actor_id=int(current_user.id),
            request=request,
            invite_count=0,
            fingerprints=[_invite_fingerprint(code)],
            outcome="not_found",
        )
        raise HTTPException(status_code=404, detail="Invite not found")

    invite.is_active = False
    db.commit()
    _audit_invite_event(
        action="revoke",
        actor_id=int(current_user.id),
        request=request,
        invite_count=1,
        fingerprints=[_invite_fingerprint(invite.code)],
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
