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
    existing = db.query(User).filter(User.email == payload.new_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already in use")

    current_user.email = payload.new_email
    current_user.email_verified = False
    db.commit()
    return MessageResponse(message="Email updated. Please verify your new email address")


@router.put("/change-username", response_model=UserResponse)
def change_username(
    payload: ChangeUsernameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
    db.delete(current_user)
    db.commit()
    return MessageResponse(message="Account deleted successfully")
