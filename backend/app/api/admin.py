"""Admin-only invite management endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin_user
from app.db.session import get_db
from app.models.invite import Invite
from app.models.user import User
from app.schemas.invite import InviteBatchCreate, InviteCreate, InviteResponse

router = APIRouter(tags=["admin"])


def _normalize_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Generate a single invite code for the invite-only beta."""
    invites = _build_invites(
        db=db,
        current_user=current_user,
        count=1,
        expires_at=payload.expires_at,
    )
    return invites[0]


@router.post("/invites/batch", response_model=list[InviteResponse])
def create_invites_batch(
    payload: InviteBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Generate multiple invite codes in one request."""
    return _build_invites(
        db=db,
        current_user=current_user,
        count=payload.count,
        expires_at=payload.expires_at,
    )


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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_user),
):
    """Soft-revoke an invite code while keeping the audit trail intact."""
    invite = db.query(Invite).filter(Invite.code == code).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    invite.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
