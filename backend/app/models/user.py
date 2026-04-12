from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
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

    email_notifications = Column(Boolean, nullable=False, default=True, server_default='true')
    reminder_notifications = Column(Boolean, nullable=False, default=True, server_default='true')
    status_update_emails = Column(Boolean, nullable=False, default=True, server_default='true')
    language = Column(String(10), nullable=False, default="en", server_default="'en'")
    timezone = Column(String(64), nullable=False, default="America/New_York", server_default="'America/New_York'")

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
    job_id = Column(Integer, nullable=False)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    url = Column(String(255), nullable=False)
