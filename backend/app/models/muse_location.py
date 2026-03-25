from sqlalchemy import Boolean, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class MuseSupportedLocation(Base):
    __tablename__ = "muse_supported_locations"
    __table_args__ = (
        UniqueConstraint("normalized_key", name="uq_muse_supported_locations_normalized_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    location_name = Column(String(255), nullable=False)
    normalized_key = Column(String(255), nullable=False, index=True)
    country_code = Column(String(2), nullable=False, index=True)
    country_name = Column(String(120), nullable=True)
    observed_count = Column(Integer, nullable=False, default=0)
    active = Column(Boolean, nullable=False, default=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())