from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class DeletedIdentity(Base):
    __tablename__ = "deleted_identities"
    __table_args__ = (
        UniqueConstraint("email", name="uq_deleted_identities_email"),
        UniqueConstraint("google_id", name="uq_deleted_identities_google_id"),
        CheckConstraint("email IS NOT NULL OR google_id IS NOT NULL", name="ck_deleted_identities_has_identity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    google_id = Column(String(255), nullable=True, index=True)
    deleted_user_id = Column(Integer, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())