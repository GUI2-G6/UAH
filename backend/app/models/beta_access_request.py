from sqlalchemy import Column, DateTime, Integer, String, text
from sqlalchemy.sql import func

from app.db.base import Base


class BetaAccessRequest(Base):
    __tablename__ = "beta_access_requests"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), nullable=False, index=True)
    full_name = Column(String(120), nullable=True)
    source_surface = Column(String(64), nullable=True)
    notes = Column(String(1200), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
