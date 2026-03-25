from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class ParseJob(Base):
    __tablename__ = "parse_jobs"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    method = Column(String(50), nullable=False)  # 'llm' or 'rules'
    status = Column(String(50), nullable=False, default="queued")  # queued|parsing|validating|success|failed|cancelled
    progress_stage = Column(String(100), nullable=True)  # human-readable stage label
    error_code = Column(String(100), nullable=True)
    error_message = Column(String(500), nullable=True)
    result_summary = Column(JSON, nullable=True)  # lightweight summary for polling (e.g. field counts)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
