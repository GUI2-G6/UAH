from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.db.base import Base


class ApplicantProfile(Base):
    __tablename__ = "applicant_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False, default="Default")
    is_active = Column(Boolean, default=True)

    # Personal
    first_name = Column(String(100), nullable=True)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    full_legal_name = Column(String(255), nullable=True)
    preferred_name = Column(String(100), nullable=True)
    suffix = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    linkedin = Column(String(255), nullable=True)
    portfolio = Column(String(255), nullable=True)

    # Address
    street_address = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    zip = Column(String(20), nullable=True)

    # Professional
    summary = Column(Text, nullable=True)
    work_auth = Column(String(100), nullable=True)
    requires_sponsorship = Column(String(50), nullable=True)

    # Education
    degree = Column(String(100), nullable=True)
    major = Column(String(100), nullable=True)
    university = Column(String(200), nullable=True)
    grad_year = Column(String(10), nullable=True)
    gpa = Column(String(20), nullable=True)

    # Experience
    years_experience = Column(String(20), nullable=True)
    job_title = Column(String(150), nullable=True)

    # Multi-value text fields (stored as text, parsed client-side)
    skills_text = Column(Text, nullable=True)
    certifications_text = Column(Text, nullable=True)
    professional_links_text = Column(Text, nullable=True)
    education_history_text = Column(Text, nullable=True)
    employment_history_text = Column(Text, nullable=True)
    canonical_data = Column(JSON, nullable=True)
    token_map = Column(JSON, nullable=True)

    # Demographics
    demographic_gender = Column(String(50), nullable=True)
    demographic_ethnicity = Column(String(100), nullable=True)

    # EEO / Job Info
    veteran_status = Column(String(200), nullable=True)
    disability_status = Column(String(200), nullable=True)
    california_resident = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
