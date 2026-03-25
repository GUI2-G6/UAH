from pydantic import BaseModel
from datetime import datetime


class ProfileBase(BaseModel):
    name: str = "Default"
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    portfolio: str | None = None
    street_address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    summary: str | None = None
    work_auth: str | None = None
    requires_sponsorship: str | None = None
    degree: str | None = None
    major: str | None = None
    university: str | None = None
    grad_year: str | None = None
    gpa: str | None = None
    years_experience: str | None = None
    job_title: str | None = None
    skills_text: str | None = None
    certifications_text: str | None = None
    professional_links_text: str | None = None
    education_history_text: str | None = None
    employment_history_text: str | None = None
    demographic_gender: str | None = None
    demographic_ethnicity: str | None = None
    veteran_status: str | None = None
    disability_status: str | None = None
    california_resident: str | None = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    name: str | None = None


class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProfileListItem(BaseModel):
    id: int
    name: str
    is_active: bool
    first_name: str | None
    last_name: str | None
    created_at: datetime

    class Config:
        from_attributes = True
