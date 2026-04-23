from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.base import Base


class LandingFeedbackSubmission(Base):
    __tablename__ = "landing_feedback_submissions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), nullable=False, index=True)
    full_name = Column(String(120), nullable=True)
    frustration = Column(Text, nullable=True)
    features = Column(Text, nullable=True)
    notify_public = Column(Boolean, nullable=False, default=False)
    interested_beta = Column(Boolean, nullable=False, default=False)
    source_surface = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
