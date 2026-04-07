from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class ApplySession(Base):
    __tablename__ = "apply_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    ats_url = Column(String(1024), nullable=True)
    job_url = Column(String(1024), nullable=True)
    status = Column(String(50), default="started")
    platform = Column(String(100), nullable=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    fields_matched = Column(Integer, nullable=True)
    fields_filled = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    finalized_at = Column(DateTime(timezone=True), nullable=True)


class ApplySessionEvent(Base):
    __tablename__ = "apply_session_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("apply_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
