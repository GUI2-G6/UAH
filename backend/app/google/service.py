from sqlalchemy.orm import Session
from app.models.user import User


class GoogleAuthService:
    @staticmethod
    def _unique_username(db: Session, preferred: str) -> str:
        base = (preferred or "user").strip().lower()
        if not base:
            base = "user"

        candidate = base
        suffix = 1
        while db.query(User).filter(User.username == candidate).first():
            suffix += 1
            candidate = f"{base}{suffix}"
        return candidate

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
        # Prefer existing account already linked by Google subject id.
        user = db.query(User).filter(User.google_id == google_id).first()

        # Fall back to matching by email so existing local accounts can link.
        if not user:
            user = db.query(User).filter(User.email == email).first()

        if user:
            if not user.google_id:
                user.google_id = google_id
            if picture_url:
                user.picture_url = picture_url
            if full_name and not user.full_name:
                user.full_name = full_name
            if email_verified:
                user.email_verified = True
        else:
            local_part = (email.split("@")[0] if "@" in email else "user").strip().lower()
            username = cls._unique_username(db, local_part)
            user = User(
                google_id=google_id,
                email=email,
                username=username,
                full_name=full_name,
                picture_url=picture_url,
                email_verified=bool(email_verified),
                is_active=True,
            )
            db.add(user)

        db.commit()
        db.refresh(user)
        return user
