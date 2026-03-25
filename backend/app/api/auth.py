from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


ADMIN_EMAIL = "admincontact@uahapp.com"


def _ensure_admin_user(db: Session) -> User:
    admin_username = os.getenv("ADMIN_BOOTSTRAP_USERNAME")
    admin_password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD")
    admin_first_name = os.getenv("ADMIN_BOOTSTRAP_FIRST_NAME")
    admin_last_name = os.getenv("ADMIN_BOOTSTRAP_LAST_NAME")

    missing = [
        name
        for name, value in {
            "ADMIN_BOOTSTRAP_USERNAME": admin_username,
            "ADMIN_BOOTSTRAP_PASSWORD": admin_password,
            "ADMIN_BOOTSTRAP_FIRST_NAME": admin_first_name,
            "ADMIN_BOOTSTRAP_LAST_NAME": admin_last_name,
        }.items()
        if not value
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Admin bootstrap env vars missing: {', '.join(missing)}",
        )

    user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if user:
        if not user.hashed_password:
            user.hashed_password = hash_password(admin_password)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    user = User(
        email=ADMIN_EMAIL,
        username=admin_username,
        hashed_password=hash_password(admin_password),
        first_name=admin_first_name,
        last_name=admin_last_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class BypassRequest(BaseModel):
    passphrase: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account."""
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    """Log in with username and password."""
    user = db.query(User).filter(User.username == payload.username).first()

    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/bypass", response_model=TokenResponse)
def bypass(payload: BypassRequest, db: Session = Depends(get_db)):
    """Alpha-only bypass: exchange a server-side passphrase for an admin JWT."""
    expected = os.getenv("ADMIN_BYPASS_PASSPHRASE")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ADMIN_BYPASS_PASSPHRASE is not set",
        )

    if payload.passphrase != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bypass passphrase",
        )

    admin_user = _ensure_admin_user(db)
    token = create_access_token(data={"sub": str(admin_user.id)})
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(admin_user),
    )


@router.get("/me", response_model=UserResponse)
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """Get the currently authenticated user's profile."""
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
