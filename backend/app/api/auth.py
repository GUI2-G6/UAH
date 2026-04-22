from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
import os
from app.api.account import trigger_verification_email_flow
from app.db.session import get_db
from app.models.invite import Invite
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse, MessageResponse
from app.core.security import hash_password, verify_password
from app.core.auth_session import (
    access_token_expire_seconds_for_client,
    create_access_token_for_client,
    resolve_auth_client,
)
from app.core.auth_cookie import clear_auth_cookie, set_auth_cookie, set_no_store_headers
from app.core.config import settings
from app.core.validation import normalize_email, require_valid_email
from app.core.rate_limit import enforce_ip_rate_limit, enforce_subject_rate_limit
from app.api.deps import get_current_user as get_authenticated_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

REGISTER_IP_LIMIT = 12
REGISTER_IP_WINDOW_SECONDS = 600
REGISTER_EMAIL_LIMIT = 4
REGISTER_EMAIL_WINDOW_SECONDS = 1800
LOGIN_IP_LIMIT = 20
LOGIN_IP_WINDOW_SECONDS = 300
LOGIN_IDENTIFIER_LIMIT = 8
LOGIN_IDENTIFIER_WINDOW_SECONDS = 300
TOKEN_IP_LIMIT = 20
TOKEN_IP_WINDOW_SECONDS = 300
TOKEN_IDENTIFIER_LIMIT = 8
TOKEN_IDENTIFIER_WINDOW_SECONDS = 300


ADMIN_EMAIL = "admincontact@uahapp.com"
EMAIL_VERIFICATION_REQUIRED_MESSAGE = (
    "Please verify your email address before logging in. Check your inbox for a verification link."
)


def _ensure_admin_user(db: Session) -> User:
    admin_password = (os.getenv("ADMIN_BOOTSTRAP_PASSWORD") or "").strip()
    admin_first_name = (os.getenv("ADMIN_BOOTSTRAP_FIRST_NAME") or "").strip() or "Admin"
    admin_last_name = (os.getenv("ADMIN_BOOTSTRAP_LAST_NAME") or "").strip() or "UAH"

    if not admin_password:
        raise ValueError("ADMIN_BOOTSTRAP_PASSWORD is required to create or repair the admin contact account.")

    normalized_admin_email = normalize_email(ADMIN_EMAIL)
    user = db.query(User).filter(func.lower(User.email) == normalized_admin_email).first()
    if user:
        if not user.hashed_password:
            user.hashed_password = hash_password(admin_password)
        if user.username != normalized_admin_email:
            user.username = normalized_admin_email
        if user.email != normalized_admin_email:
            user.email = normalized_admin_email
        user.is_admin = True
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
def register(
    payload: UserRegister,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Register a new user account and return an access token.

    Creates a local credential-based account after validating that the submitted
    email is not already in use. On success, this endpoint returns
    a bearer token and the normalized user profile so the frontend can treat
    registration as an authenticated session.

    Response codes:
    - 201: Account created successfully and token issued.
    - 400: Email already registered, or invite code is invalid/expired.
    - 422: Request validation failed (for example, missing fields).
    - 500: Server/database error while creating the account.
    """
    enforce_ip_rate_limit(
        "auth:register",
        request,
        limit=REGISTER_IP_LIMIT,
        window_seconds=REGISTER_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "auth:register:email",
        payload.email,
        limit=REGISTER_EMAIL_LIMIT,
        window_seconds=REGISTER_EMAIL_WINDOW_SECONDS,
    )

    normalized_email = require_valid_email(payload.email)

    if db.query(User).filter(func.lower(User.email) == normalized_email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    invite_code = str(payload.invite_code or "").strip()
    invite = (
        db.query(Invite)
        .with_for_update()
        .filter(
            Invite.code == invite_code,
            Invite.is_active.is_(True),
            Invite.use_count < Invite.max_uses,
            or_(Invite.expires_at.is_(None), Invite.expires_at > datetime.now(timezone.utc)),
        )
        .first()
    )
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite code",
        )

    user = User(
        email=normalized_email,
        username=normalized_email,
        hashed_password=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(user)
    db.flush()

    invite.use_count = int(invite.use_count or 0) + 1
    invite.used_by = user.id
    invite.used_at = datetime.now(timezone.utc)
    if invite.use_count >= int(invite.max_uses or 1):
        invite.is_active = False
    user.invite_code_used = invite.code

    trigger_verification_email_flow(db=db, user=user)

    auth_client = resolve_auth_client(request)
    token = create_access_token_for_client(data={"sub": str(user.id)}, client=auth_client)
    set_auth_cookie(response, token, max_age=access_token_expire_seconds_for_client(auth_client))
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: UserLogin,
    request: Request,
    response: Response,
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
    - 403: Account exists but is deactivated or email verification is still pending.
           For unverified users, a fresh verification email is sent before returning 403.
    - 500: Verification email could not be sent for an unverified account.
    - 422: Request validation failed.
    """
    enforce_ip_rate_limit(
        "auth:login",
        request,
        limit=LOGIN_IP_LIMIT,
        window_seconds=LOGIN_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "auth:login:identifier",
        payload.email,
        limit=LOGIN_IDENTIFIER_LIMIT,
        window_seconds=LOGIN_IDENTIFIER_WINDOW_SECONDS,
    )

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
    if not user.email_verified:
        trigger_verification_email_flow(db=db, user=user)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=EMAIL_VERIFICATION_REQUIRED_MESSAGE,
        )

    auth_client = resolve_auth_client(request)
    token = create_access_token_for_client(data={"sub": str(user.id)}, client=auth_client)
    set_auth_cookie(response, token, max_age=access_token_expire_seconds_for_client(auth_client))
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/token")
def token_login(
    request: Request,
    response: Response,
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
    - 403: Account is deactivated or email verification is still pending.
           For unverified users, a fresh verification email is sent before returning 403.
    - 500: Verification email could not be sent for an unverified account.
    - 422: Invalid form payload.
    """
    enforce_ip_rate_limit(
        "auth:token",
        request,
        limit=TOKEN_IP_LIMIT,
        window_seconds=TOKEN_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "auth:token:identifier",
        form_data.username,
        limit=TOKEN_IDENTIFIER_LIMIT,
        window_seconds=TOKEN_IDENTIFIER_WINDOW_SECONDS,
    )

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
    if not user.email_verified:
        trigger_verification_email_flow(db=db, user=user)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=EMAIL_VERIFICATION_REQUIRED_MESSAGE,
        )

    auth_client = resolve_auth_client(request)
    token = create_access_token_for_client(data={"sub": str(user.id)}, client=auth_client)
    set_auth_cookie(response, token, max_age=access_token_expire_seconds_for_client(auth_client))
    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    clear_auth_cookie(response)
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=UserResponse)
def read_current_user(
    response: Response,
    current_user: User = Depends(get_authenticated_user),
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
    set_no_store_headers(response)
    return current_user
