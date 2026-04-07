from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
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
from app.core.config import settings
from app.services.email import send_email, EmailNotConfiguredError

router = APIRouter(prefix="/api/account", tags=["account"])


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Begin password reset flow for an email address.

    Generates a password-reset token when the account exists and either emails
    it (production) or returns a dev-only token string when outbound email is
    disabled. The response is intentionally generic to reduce account enumeration.

    Response codes:
    - 200: Reset flow accepted (message always returned).
    - 500: Email infrastructure not configured or send failure.
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        return MessageResponse(message="If that email exists, a reset link has been sent")

    token = create_verification_token(user.id, purpose="password_reset")

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
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Complete password reset using a verification token.

    Validates a password-reset token, locates the target user, hashes the new
    password, and persists it to the account.

    Response codes:
    - 200: Password reset completed successfully.
    - 400: Token is invalid or expired.
    - 404: Token is valid but target user does not exist.
    """
    decoded = decode_verification_token(payload.token, expected_purpose="password_reset")
    if decoded is None:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.query(User).filter(User.id == int(decoded["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return MessageResponse(message="Password has been reset successfully")


@router.put("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
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
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="Account uses OAuth login, no password to change")

    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
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
    existing = db.query(User).filter(User.email == payload.new_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")

    old_email = current_user.email
    current_user.email = payload.new_email
    current_user.email_verified = False
    db.commit()

    if settings.EMAILS_ENABLED and old_email:
        try:
            send_email(
                to=old_email,
                subject="UAH account email changed",
                text=(
                    f"The email on your UAH account was just changed to {payload.new_email}.\n\n"
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
    Update username for the current user.

    Ensures the new username is unique before persisting and returning the
    updated user profile.

    Response codes:
    - 200: Username changed successfully.
    - 400: Username already taken by another account.
    """
    existing = db.query(User).filter(User.username == payload.new_username).first()
    if existing and existing.id != current_user.id:
        raise HTTPException(status_code=400, detail="Username already taken")

    current_user.username = payload.new_username
    db.commit()
    db.refresh(current_user)
    return current_user


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
    if current_user.email_verified:
        return MessageResponse(message="Email is already verified")

    if not current_user.email:
        raise HTTPException(status_code=400, detail="No email set on this account")

    token = create_verification_token(current_user.id, purpose="email_verify")

    if not settings.EMAILS_ENABLED:
        return MessageResponse(message=f"Verification token (dev only): {token}")

    public_url = (settings.PUBLIC_APP_URL or "").rstrip("/")
    text = (
        "Verify your email for your UAH account.\n\n"
        f"Verification token: {token}\n"
    )
    if public_url:
        text += f"\nOpen Settings to paste the token: {public_url}/settings\n"

    try:
        send_email(
            to=current_user.email,
            subject="Verify your UAH email",
            text=text,
        )
    except EmailNotConfiguredError as e:
        raise HTTPException(status_code=500, detail=f"Email not configured: {e}")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send verification email")

    return MessageResponse(message="Verification email sent")


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verify an email address using a signed verification token.

    Validates the token purpose and subject, then marks the target user's
    `email_verified` flag as true.

    Response codes:
    - 200: Email verification completed.
    - 400: Token is invalid, malformed, or expired.
    - 404: Token subject user not found.
    """
    decoded = decode_verification_token(payload.token, expected_purpose="email_verify")
    if decoded is None:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    user = db.query(User).filter(User.id == int(decoded["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.email_verified = True
    db.commit()
    return MessageResponse(message="Email verified successfully")


@router.delete("/delete", response_model=MessageResponse)
def delete_account(
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
    db.delete(current_user)
    db.commit()
    return MessageResponse(message="Account deleted successfully")
