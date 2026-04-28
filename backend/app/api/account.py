from datetime import datetime, timedelta, timezone
import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.invite import Invite
from app.models.user import User
from app.models.user import SavedJob
from app.api.deps import get_current_user
from app.schemas.user import (
    ChangePasswordRequest, ResetPasswordRequest, ForgotPasswordRequest,
    ChangeEmailRequest, ChangeUsernameRequest, VerifyEmailRequest,
    ChangeNameRequest,
    MessageResponse, UserResponse,
)
from app.core.security import (
    hash_password, verify_password,
    create_verification_token, decode_verification_token,
)
from app.core.auth_cookie import clear_auth_cookie
from app.core.config import settings
from app.core.rate_limit import enforce_ip_rate_limit, enforce_subject_rate_limit
from app.core.validation import normalize_email, require_valid_email
from app.services.deleted_identities import record_deleted_identities_for_user
from app.services.email import send_email, EmailNotConfiguredError

router = APIRouter(prefix="/api/account", tags=["account"])

ACCOUNT_TOKEN_TTL = timedelta(hours=24)
FORGOT_PASSWORD_IP_LIMIT = 8
FORGOT_PASSWORD_IP_WINDOW_SECONDS = 900
FORGOT_PASSWORD_EMAIL_LIMIT = 4
FORGOT_PASSWORD_EMAIL_WINDOW_SECONDS = 1800
RESET_PASSWORD_IP_LIMIT = 12
RESET_PASSWORD_IP_WINDOW_SECONDS = 900
RESET_PASSWORD_TOKEN_LIMIT = 6
RESET_PASSWORD_TOKEN_WINDOW_SECONDS = 1800
SEND_VERIFICATION_IP_LIMIT = 6
SEND_VERIFICATION_IP_WINDOW_SECONDS = 900
SEND_VERIFICATION_USER_LIMIT = 4
SEND_VERIFICATION_USER_WINDOW_SECONDS = 1800
VERIFY_EMAIL_IP_LIMIT = 12
VERIFY_EMAIL_IP_WINDOW_SECONDS = 900
VERIFY_EMAIL_TOKEN_LIMIT = 6
VERIFY_EMAIL_TOKEN_WINDOW_SECONDS = 1800
CHANGE_PASSWORD_IP_LIMIT = 8
CHANGE_PASSWORD_IP_WINDOW_SECONDS = 900
CHANGE_PASSWORD_USER_LIMIT = 5
CHANGE_PASSWORD_USER_WINDOW_SECONDS = 1800


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _datetime_has_expired(value: datetime | None) -> bool:
    expires_at = _normalize_utc_datetime(value)
    if expires_at is None:
        return True
    return expires_at <= _utcnow()


def _clear_password_reset_state(user: User) -> None:
    user.password_reset_token_id = None
    user.password_reset_expires_at = None


def _clear_email_verification_state(user: User) -> None:
    user.email_verify_token_id = None
    user.email_verify_target_email = None
    user.email_verify_expires_at = None


def _issue_password_reset_token(user: User) -> str:
    token_id = secrets.token_urlsafe(32)
    expires_at = _utcnow() + ACCOUNT_TOKEN_TTL
    user.password_reset_token_id = token_id
    user.password_reset_expires_at = expires_at
    return create_verification_token(
        user.id,
        purpose="password_reset",
        expires_delta=ACCOUNT_TOKEN_TTL,
        jti=token_id,
    )


def _issue_email_verification_token(user: User, target_email: str) -> str:
    normalized_target_email = require_valid_email(target_email, field_name="target_email")
    token_id = secrets.token_urlsafe(32)
    expires_at = _utcnow() + ACCOUNT_TOKEN_TTL
    user.email_verify_token_id = token_id
    user.email_verify_target_email = normalized_target_email
    user.email_verify_expires_at = expires_at
    return create_verification_token(
        user.id,
        purpose="email_verify",
        expires_delta=ACCOUNT_TOKEN_TTL,
        jti=token_id,
        email=normalized_target_email,
    )


def _build_verify_email_link(token: str) -> str | None:
    public_url = (settings.PUBLIC_APP_URL or "").rstrip("/")
    if not public_url:
        return None
    return f"{public_url}/verify-email?token={quote(token, safe='')}"


def trigger_verification_email_flow(db: Session, user: User) -> MessageResponse:
    if user.email_verified:
        return MessageResponse(message="Email is already verified")

    if not user.email:
        raise HTTPException(status_code=400, detail="No email set on this account")

    token = _issue_email_verification_token(user, user.email)

    if not settings.EMAILS_ENABLED:
        db.commit()
        db.refresh(user)
        return MessageResponse(message=f"Verification token (dev only): {token}")

    verify_link = _build_verify_email_link(token)
    if verify_link:
        text = (
            "Verify your email for your UAH account.\n\n"
            "Use the secure verification link below:\n"
            f"{verify_link}\n"
        )
    else:
        text = (
            "Verify your email for your UAH account.\n\n"
            f"Verification token: {token}\n"
        )

    try:
        send_email(
            to=user.email,
            subject="Verify your UAH email",
            text=text,
        )
    except EmailNotConfiguredError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Email not configured: {e}")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to send verification email")

    db.commit()
    db.refresh(user)
    return MessageResponse(message="Verification email sent")


def _password_reset_token_is_valid(user: User, decoded: dict | None) -> bool:
    if not decoded:
        return False

    token_id = str(decoded.get("jti") or "").strip()
    stored_token_id = str(user.password_reset_token_id or "").strip()
    if not token_id or not stored_token_id or token_id != stored_token_id:
        return False

    return not _datetime_has_expired(user.password_reset_expires_at)


def _email_verification_token_is_valid(user: User, decoded: dict | None) -> bool:
    if not decoded:
        return False

    token_id = str(decoded.get("jti") or "").strip()
    stored_token_id = str(user.email_verify_token_id or "").strip()
    if not token_id or not stored_token_id or token_id != stored_token_id:
        return False

    token_email = normalize_email(decoded.get("email"))
    stored_target_email = normalize_email(user.email_verify_target_email)
    current_email = normalize_email(user.email)
    if not token_email or not stored_target_email or token_email != stored_target_email:
        return False
    if not current_email or current_email != stored_target_email:
        return False

    return not _datetime_has_expired(user.email_verify_expires_at)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Begin password reset flow for an email address.

    Generates a password-reset token when the account exists and either emails
    it (production) or returns a dev-only token string when outbound email is
    disabled. The response is intentionally generic to reduce account enumeration.

    Response codes:
    - 200: Reset flow accepted (message always returned).
    - 500: Email infrastructure not configured or send failure.
    """
    enforce_ip_rate_limit(
        "account:forgot-password",
        request,
        limit=FORGOT_PASSWORD_IP_LIMIT,
        window_seconds=FORGOT_PASSWORD_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "account:forgot-password:email",
        payload.email,
        limit=FORGOT_PASSWORD_EMAIL_LIMIT,
        window_seconds=FORGOT_PASSWORD_EMAIL_WINDOW_SECONDS,
    )

    normalized_email = require_valid_email(payload.email)
    user = db.query(User).filter(func.lower(User.email) == normalized_email).first()

    if not user:
        return MessageResponse(message="If that email exists, a reset link has been sent")

    token = _issue_password_reset_token(user)
    db.commit()

    if not settings.EMAILS_ENABLED:
        return MessageResponse(message=f"Reset token (dev only): {token}")

    public_url = (settings.PUBLIC_APP_URL or "").rstrip("/")
    text = (
        "You requested a password reset for your UAH account.\n\n"
        f"Reset token: {token}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )
    if public_url:
        text += f"\nOpen Settings to paste the token: {public_url}/settings\n"

    try:
        send_email(
            to=user.email,
            subject="UAH password reset",
            text=text,
        )
    except EmailNotConfiguredError as e:
        raise HTTPException(status_code=500, detail=f"Email not configured: {e}")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send reset email")

    return MessageResponse(message="If that email exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Complete password reset using a verification token.

    Validates a password-reset token, locates the target user, hashes the new
    password, and persists it to the account.

    Response codes:
    - 200: Password reset completed successfully.
    - 400: Token is invalid or expired.
    - 404: Token is valid but target user does not exist.
    """
    enforce_ip_rate_limit(
        "account:reset-password",
        request,
        limit=RESET_PASSWORD_IP_LIMIT,
        window_seconds=RESET_PASSWORD_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "account:reset-password:token",
        payload.token,
        limit=RESET_PASSWORD_TOKEN_LIMIT,
        window_seconds=RESET_PASSWORD_TOKEN_WINDOW_SECONDS,
    )

    decoded = decode_verification_token(payload.token, expected_purpose="password_reset")
    if decoded is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == int(decoded["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _password_reset_token_is_valid(user, decoded):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(payload.new_password)
    _clear_password_reset_state(user)
    db.commit()
    return MessageResponse(message="Password has been reset successfully")


@router.put("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Change password for the currently authenticated user.

    Requires current password re-verification for local accounts before storing
    the new password hash.

    Response codes:
    - 200: Password changed successfully.
    - 400: Account is OAuth-only and has no local password.
    - 401: Current password is incorrect.
    """
    enforce_ip_rate_limit(
        "account:change-password",
        request,
        limit=CHANGE_PASSWORD_IP_LIMIT,
        window_seconds=CHANGE_PASSWORD_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "account:change-password:user",
        current_user.id,
        limit=CHANGE_PASSWORD_USER_LIMIT,
        window_seconds=CHANGE_PASSWORD_USER_WINDOW_SECONDS,
    )

    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="Account uses OAuth login, no password to change")

    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
    _clear_password_reset_state(current_user)
    db.commit()
    return MessageResponse(message="Password changed successfully")


@router.put("/change-email", response_model=MessageResponse)
def change_email(
    payload: ChangeEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update email address for the current user.

    Enforces email uniqueness across all accounts and marks the new address as
    unverified until the verification flow is completed.

    Response codes:
    - 200: Email updated and verification required.
    - 400: Email already belongs to another account.
    """
    normalized_new_email = require_valid_email(payload.new_email, field_name="new_email")
    existing = db.query(User).filter(func.lower(User.email) == normalized_new_email).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="Email already in use")

    old_email = current_user.email

    if not current_user.email_verified:
        token = _issue_email_verification_token(current_user, old_email)
        db.commit()
        verify_link = _build_verify_email_link(token)
        if not settings.EMAILS_ENABLED:
            return MessageResponse(
                message=f"You must verify your current email first. Verification token (dev only): {token}"
            )
        try:
            body = (
                "You requested an email change on your UAH account, but your current email "
                "is not yet verified. Please verify it first.\n\n"
            )
            if verify_link:
                body += (
                    "Use the secure verification link below:\n"
                    f"{verify_link}\n"
                )
            else:
                body += f"Verification token: {token}\n"
            send_email(
                to=old_email,
                subject="Verify your current email — UAH",
                text=body,
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=400,
            detail="Your current email must be verified before changing it. A verification email has been sent."
        )

    current_user.email = normalized_new_email
    current_user.username = normalized_new_email
    current_user.email_verified = False
    _clear_email_verification_state(current_user)
    db.commit()

    if settings.EMAILS_ENABLED and old_email:
        try:
            send_email(
                to=old_email,
                subject="UAH account email changed",
                text=(
                    f"The email on your UAH account was just changed to {normalized_new_email}.\n\n"
                    "If you did not make this change, please contact support immediately.\n"
                ),
            )
        except Exception:
            pass

    return MessageResponse(message="Email updated. Please verify your new email address")


@router.put("/change-username", response_model=UserResponse)
def change_username(
    payload: ChangeUsernameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deprecated endpoint retained temporarily for compatibility.

    Response codes:
    - 410: Username updates are no longer supported.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="Username updates are deprecated. Email is now the sign-in identifier.",
    )


@router.put("/change-name", response_model=UserResponse)
def change_name(
    payload: ChangeNameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update first and/or last name for the current user.

    Accepts partial updates and normalizes blank values to null. This endpoint
    supports both local and OAuth-authenticated accounts.

    Response codes:
    - 200: Name fields updated successfully.
    """
    # Allow users (including OAuth accounts) to update their profile name.
    current_user.first_name = payload.first_name.strip() if payload.first_name and payload.first_name.strip() else None
    current_user.last_name = payload.last_name.strip() if payload.last_name and payload.last_name.strip() else None
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/send-verification", response_model=MessageResponse)
def send_verification_email(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate and send an email verification token.

    If email delivery is disabled, a dev-only token is returned in the response.
    If the account is already verified, the endpoint returns a no-op success
    message to keep client behavior simple.

    Response codes:
    - 200: Verification flow handled successfully.
    - 400: User has no email address configured.
    - 500: Email configuration or delivery failure.
    """
    enforce_ip_rate_limit(
        "account:send-verification",
        request,
        limit=SEND_VERIFICATION_IP_LIMIT,
        window_seconds=SEND_VERIFICATION_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "account:send-verification:user",
        current_user.id,
        limit=SEND_VERIFICATION_USER_LIMIT,
        window_seconds=SEND_VERIFICATION_USER_WINDOW_SECONDS,
    )

    if current_user.email_verified:
        return MessageResponse(message="Email is already verified")
    return trigger_verification_email_flow(db=db, user=current_user)


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Verify an email address using a signed verification token.

    Validates the token purpose and subject, then marks the target user's
    `email_verified` flag as true.

    Response codes:
    - 200: Email verification completed.
    - 400: Token is invalid, malformed, or expired.
    - 404: Token subject user not found.
    """
    enforce_ip_rate_limit(
        "account:verify-email",
        request,
        limit=VERIFY_EMAIL_IP_LIMIT,
        window_seconds=VERIFY_EMAIL_IP_WINDOW_SECONDS,
    )
    enforce_subject_rate_limit(
        "account:verify-email:token",
        payload.token,
        limit=VERIFY_EMAIL_TOKEN_LIMIT,
        window_seconds=VERIFY_EMAIL_TOKEN_WINDOW_SECONDS,
    )

    decoded = decode_verification_token(payload.token, expected_purpose="email_verify")
    if decoded is None:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user = db.query(User).filter(User.id == int(decoded["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not _email_verification_token_is_valid(user, decoded):
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user.email_verified = True
    _clear_email_verification_state(user)
    db.commit()
    return MessageResponse(message="Email verified successfully")


@router.delete("/delete", response_model=MessageResponse)
def delete_account(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Permanently delete the currently authenticated account.

    Removes the current user record and returns a confirmation message. This is
    a destructive action and should generally be guarded by a frontend confirm
    dialog.

    Response codes:
    - 200: Account deleted successfully.
    """
    record_deleted_identities_for_user(db, current_user)

    # Remove detached user artifacts and preserve invite safety before hard-delete.
    db.query(SavedJob).filter(SavedJob.user_id == current_user.id).delete(synchronize_session=False)
    db.query(Invite).filter(Invite.created_by == current_user.id).delete(synchronize_session=False)
    db.query(Invite).filter(Invite.used_by == current_user.id).update(
        {
            Invite.used_by: None,
        },
        synchronize_session=False,
    )

    db.delete(current_user)
    db.commit()
    clear_auth_cookie(response)
    return MessageResponse(message="Account deleted successfully")
