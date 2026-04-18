from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.validation import normalize_email
from app.models.deleted_identity import DeletedIdentity
from app.models.user import User


def _normalize_google_id(value: str | None) -> str:
    return str(value or "").strip()


def _identity_filter(normalized_email: str | None, normalized_google_id: str | None):
    clauses = []
    if normalized_email:
        clauses.append(DeletedIdentity.email == normalized_email)
    if normalized_google_id:
        clauses.append(DeletedIdentity.google_id == normalized_google_id)
    if not clauses:
        return None
    return or_(*clauses)


def _active_user_exists(
    db: Session,
    *,
    normalized_email: str | None,
    normalized_google_id: str | None,
) -> bool:
    clauses = []
    if normalized_email:
        clauses.append(func.lower(User.email) == normalized_email)
    if normalized_google_id:
        clauses.append(User.google_id == normalized_google_id)
    if not clauses:
        return False
    return db.query(User.id).filter(or_(*clauses)).first() is not None


def purge_stale_deleted_identities(
    db: Session,
    *,
    email: str | None = None,
    google_id: str | None = None,
) -> int:
    normalized_email = normalize_email(email) or None
    normalized_google_id = _normalize_google_id(google_id) or None
    identity_clause = _identity_filter(normalized_email, normalized_google_id)
    if identity_clause is None:
        return 0

    if not _active_user_exists(
        db,
        normalized_email=normalized_email,
        normalized_google_id=normalized_google_id,
    ):
        return 0

    deleted = (
        db.query(DeletedIdentity)
        .filter(identity_clause)
        .delete(synchronize_session=False)
    )
    return int(deleted or 0)


def ensure_identity_not_blocked(
    db: Session,
    *,
    email: str | None = None,
    google_id: str | None = None,
) -> None:
    normalized_email = normalize_email(email) or None
    normalized_google_id = _normalize_google_id(google_id) or None
    identity_clause = _identity_filter(normalized_email, normalized_google_id)
    if identity_clause is None:
        return

    purged = purge_stale_deleted_identities(
        db,
        email=normalized_email,
        google_id=normalized_google_id,
    )
    if purged:
        db.flush()

    blocked = db.query(DeletedIdentity.id).filter(identity_clause).first()
    if blocked:
        raise ValueError("account_deleted")


def _upsert_tombstone(
    db: Session,
    *,
    field: str,
    value: str,
    deleted_user_id: int,
    deleted_at: datetime,
) -> None:
    identity = db.query(DeletedIdentity).filter(getattr(DeletedIdentity, field) == value).first()
    if identity:
        identity.deleted_user_id = deleted_user_id
        identity.deleted_at = deleted_at
        return

    payload = {
        field: value,
        "deleted_user_id": deleted_user_id,
        "deleted_at": deleted_at,
    }
    db.add(DeletedIdentity(**payload))


def record_deleted_identities_for_user(db: Session, user: User) -> None:
    now = datetime.now(timezone.utc)
    normalized_email = normalize_email(user.email) or None
    normalized_google_id = _normalize_google_id(user.google_id) or None

    if normalized_email:
        _upsert_tombstone(
            db,
            field="email",
            value=normalized_email,
            deleted_user_id=int(user.id),
            deleted_at=now,
        )

    if normalized_google_id:
        _upsert_tombstone(
            db,
            field="google_id",
            value=normalized_google_id,
            deleted_user_id=int(user.id),
            deleted_at=now,
        )