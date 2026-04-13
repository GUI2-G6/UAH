from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.core.security import decode_access_token
from app.core.auth_cookie import get_auth_cookie_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def get_request_token(
    request: Request,
    bearer_token: str | None = Depends(oauth2_scheme),
) -> str:
    token = (bearer_token or "").strip() or (get_auth_cookie_token(request) or "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return token


def get_current_user(db: Session = Depends(get_db), token: str = Depends(get_request_token)) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def require_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user
