from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.validation import normalize_email


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

        # Prefer existing account already linked by Google subject id.
        user = db.query(User).filter(User.google_id == google_id).first()

        # Fall back to matching by email so existing local accounts can link.
        if not user:
            email_owner = db.query(User).filter(func.lower(User.email) == normalized_email).first()
            if email_owner and not email_verified:
                raise ValueError("email_not_verified")
            user = email_owner

        if user:
            user.email = normalized_email
            user.username = normalized_email
            if not user.google_id:
                user.google_id = google_id
            if picture_url:
                user.picture_url = picture_url
            if full_name and not user.full_name:
                user.full_name = full_name
            if email_verified:
                user.email_verified = True
        else:
            user = User(
                google_id=google_id,
                email=normalized_email,
                username=normalized_email,
                full_name=full_name,
                picture_url=picture_url,
                email_verified=bool(email_verified),
                is_active=True,
            )
            db.add(user)

        db.commit()
        db.refresh(user)
        return user
