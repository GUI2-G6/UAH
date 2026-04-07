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

    linkedIn_id = Column(String(255), unique=True, nullable=True)
    google_id = Column(String(255), unique=True, nullable=True)

    full_name = Column(String(255), nullable=True)
    picture_url = Column(String(255), nullable=True)

    gmail_refresh_token = Column(Text, nullable=True)
    gmail_email = Column(String(255), nullable=True)

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
