from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, JSON, LargeBinary
from sqlalchemy.sql import func
from app.db.base import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    pdf_data = Column(LargeBinary, nullable=True)
    raw_markdown = Column(Text, nullable=True)
    raw_markdown_source = Column(String(80), nullable=True)
    raw_markdown_method = Column(String(50), nullable=True)
    raw_markdown_updated_at = Column(DateTime(timezone=True), nullable=True)
    structured_data = Column(JSON, nullable=True)
    portal_ready = Column(Boolean, default=False)
    parse_method = Column(String(50), nullable=True)
    review_status = Column(String(50), nullable=True)
    review_draft = Column(JSON, nullable=True)
    review_updated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def has_pdf(self):
        return self.pdf_data is not None

    @property
    def has_review_draft(self):
        return self.review_draft is not None
