from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
import os
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.core.validation import normalize_email, require_valid_email
from app.api.deps import oauth2_scheme

router = APIRouter(prefix="/api/auth", tags=["auth"])


ADMIN_EMAIL = "admincontact@uahapp.com"


def _ensure_admin_user(db: Session) -> User:
    admin_password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD")
    admin_first_name = os.getenv("ADMIN_BOOTSTRAP_FIRST_NAME")
    admin_last_name = os.getenv("ADMIN_BOOTSTRAP_LAST_NAME")

    missing = [
        name
        for name, value in {
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

    normalized_admin_email = normalize_email(ADMIN_EMAIL)
    user = db.query(User).filter(func.lower(User.email) == normalized_admin_email).first()
    if user:
        if not user.hashed_password:
            user.hashed_password = hash_password(admin_password)
        if user.username != normalized_admin_email:
            user.username = normalized_admin_email
        if user.email != normalized_admin_email:
            user.email = normalized_admin_email
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    user = User(
        email=normalized_admin_email,
        username=normalized_admin_email,
        hashed_password=hash_password(admin_password),
        first_name=admin_first_name,
        last_name=admin_last_name,
        is_active=True,
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user account and return an access token.

    Creates a local credential-based account after validating that the submitted
    email is not already in use. On success, this endpoint returns
    a bearer token and the normalized user profile so the frontend can treat
    registration as an authenticated session.

    Response codes:
    - 201: Account created successfully and token issued.
    - 400: Email already registered.
    - 422: Request validation failed (for example, missing fields).
    - 500: Server/database error while creating the account.
    """
    normalized_email = require_valid_email(payload.email)
    if db.query(User).filter(func.lower(User.email) == normalized_email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        email=normalized_email,
        username=normalized_email,
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
    """
    Authenticate with email and password.

    Validates submitted credentials against a local account, verifies the account
    is active, and returns a signed bearer token plus profile data. This endpoint
    is intended for the standard app login flow.

    Response codes:
    - 200: Authentication succeeded and token issued.
    - 401: Invalid email/password combination.
    - 403: Account exists but is deactivated.
    - 422: Request validation failed.
    """
    identifier = require_valid_email(payload.email)
    user = db.query(User).filter(func.lower(User.email) == identifier).first()

    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
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


@router.post("/token")
def token_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2-compatible token endpoint for Swagger Authorize and tooling.

    Accepts form-encoded credentials (`username`, `password`) using the
    OAuth2 password grant format. This route is primarily used by Swagger UI's
    Authorize dialog and other clients expecting the standard token payload.

    Response codes:
    - 200: Token generated successfully.
    - 401: Invalid email/password.
    - 403: Account is deactivated.
    - 422: Invalid form payload.
    """
    try:
        identifier = require_valid_email(form_data.username, field_name="username")
    except ValueError:
        identifier = ""
    user = db.query(User).filter(func.lower(User.email) == identifier).first()

    if not user or not user.hashed_password or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserResponse)
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    """
    Retrieve the profile of the currently authenticated user.

    Decodes and validates the bearer token from the Authorization header,
    then fetches the corresponding user record from the database.

    Response codes:
    - 200: User profile returned successfully.
    - 401: Token missing, invalid, or expired.
    - 404: Token subject is valid but user no longer exists.
    """
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
