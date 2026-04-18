from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.validation import normalize_email
from app.services.deleted_identities import ensure_identity_not_blocked


class GoogleAuthService:
    @classmethod
    def get_or_create_user(
        cls,
        db: Session,
        google_id: str,
        email: str,
        full_name: str | None,
        picture_url: str | None,
        email_verified: bool = False,
    ) -> User:
        normalized_email = normalize_email(email)
        if not normalized_email:
            raise ValueError("Google profile email is missing")

        ensure_identity_not_blocked(db, email=normalized_email, google_id=google_id)

        if not email_verified:
            raise ValueError("email_not_verified")

        # OAuth login is allowed only for accounts already linked to Google.
        user = db.query(User).filter(User.google_id == google_id).first()
        if not user:
            raise ValueError("google_not_linked")

        email_owner = (
            db.query(User)
            .filter(func.lower(User.email) == normalized_email, User.id != user.id)
            .first()
        )
        if email_owner:
            raise ValueError("email_conflict")

        user.email = normalized_email
        user.username = normalized_email
        if picture_url:
            user.picture_url = picture_url
        if full_name and not user.full_name:
            user.full_name = full_name
        user.email_verified = True

        db.commit()
        db.refresh(user)
        return user
