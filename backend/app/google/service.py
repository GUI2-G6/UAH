from sqlaclhemy.orm import Session
from app.models.user import User

class GoogleAuthService:
    @classmethod
    def get_or_create_user(
        cls,
        db: Session,
        google_id: str,
        email: str,
        full_name: str,
        picture_url: str,
    ):
    
        user = db.query(User).filter(User.email == email).first()
        if user: 
            user.google_id = google_id
            if user.picture_url:
                user.picture_url = picture_url
        else:
            user = User(
                google_id=google_id,
                email=email,
                username=email.split("@")[0],
                full_name=full_name,
                picture_url=picture_url
            )
            db.add(user)
        db.commit()
        db.refresh(user)
        return user