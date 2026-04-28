from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_developer = Column(Boolean, default=False)

    linkedIn_id = Column(String(255), unique=True, nullable=True)
    google_id = Column(String(255), unique=True, nullable=True)

    full_name = Column(String(255), nullable=True)
    picture_url = Column(String(255), nullable=True)

    gmail_refresh_token = Column(Text, nullable=True)
    gmail_email = Column(String(255), nullable=True)

    password_reset_token_id = Column(String(255), nullable=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    email_verify_token_id = Column(String(255), nullable=True)
    email_verify_target_email = Column(String(255), nullable=True)
    email_verify_expires_at = Column(DateTime(timezone=True), nullable=True)
    invite_code_used = Column(String(64), nullable=True)

    email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def avatar_url(self):
        return self.picture_url

class SavedJob(Base):
    __tablename__ = "saved_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    job_id = Column(Integer, nullable=True)
    provider = Column(String(50), nullable=True, index=True)
    provider_job_id = Column(String(255), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    url = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class GmailSuppression(Base):
    __tablename__ = "gmail_suppressions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    scope = Column(String(40), nullable=False, index=True)
    source_id = Column(String(255), nullable=True, index=True)
    sender_domain = Column(String(255), nullable=True, index=True)
    subject_key = Column(String(255), nullable=True, index=True)
    company_key = Column(String(255), nullable=True, index=True)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class GmailNotificationState(Base):
    __tablename__ = "gmail_notification_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(255), nullable=False, index=True)
    state = Column(String(40), nullable=False, index=True)
    snoozed_until = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", "source_id", name="uq_gmail_notification_states_user_source"),
    )


class GmailFeedback(Base):
    __tablename__ = "gmail_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(String(255), nullable=True, index=True)
    sender_domain = Column(String(255), nullable=True, index=True)
    subject_key = Column(String(255), nullable=True, index=True)
    company_key = Column(String(255), nullable=True, index=True)
    triage_label = Column(String(40), nullable=False, index=True)
    override_status = Column(String(40), nullable=True, index=True)
    false_positive_reason = Column(String(255), nullable=True)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
