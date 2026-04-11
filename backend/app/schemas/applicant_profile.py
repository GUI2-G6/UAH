from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from app.core.validation import normalize_phone, require_valid_email


class ProfileBase(BaseModel):
    name: str = Field(
        default="Default",
        max_length=120,
        description="Friendly profile label shown in the profile switcher (for example, Main, Internship, Senior Role).",
        examples=["Default"],
    )
    first_name: str | None = Field(default=None, max_length=100, description="Applicant first name.", examples=["Jane"])
    last_name: str | None = Field(default=None, max_length=100, description="Applicant last name.", examples=["Doe"])
    email: str | None = Field(default=None, max_length=255, description="Primary contact email for applications.", examples=["jane.doe@example.com"])
    phone: str | None = Field(default=None, max_length=40, description="Primary contact phone number including area/country code.", examples=["+1-555-010-1001"])
    linkedin: str | None = Field(default=None, max_length=500, description="Public LinkedIn profile URL.", examples=["https://www.linkedin.com/in/jane-doe/"])
    portfolio: str | None = Field(default=None, max_length=500, description="Portfolio, GitHub, or personal site URL.", examples=["https://janedoe.dev"])
    street_address: str | None = Field(default=None, max_length=200, description="Street portion of mailing or residence address.", examples=["123 Main St Apt 4B"])
    city: str | None = Field(default=None, max_length=120, description="City for location-specific applications.", examples=["Huntsville"])
    state: str | None = Field(default=None, max_length=120, description="State, province, or region.", examples=["AL"])
    zip: str | None = Field(default=None, max_length=20, description="Postal code associated with the saved address.", examples=["35801"])
    summary: str | None = Field(default=None, max_length=3000, description="Short professional summary used in quick-apply forms.", examples=["Backend engineer with 5+ years building API platforms and data pipelines."])
    work_auth: str | None = Field(default=None, max_length=120, description="Work authorization statement (for example, authorized to work in the US).", examples=["Authorized to work in the US"])
    requires_sponsorship: str | None = Field(default=None, max_length=60, description="Whether visa sponsorship is required for employment.", examples=["No"])
    degree: str | None = Field(default=None, max_length=120, description="Highest degree earned or currently pursued.", examples=["Bachelor of Science"])
    major: str | None = Field(default=None, max_length=120, description="Academic major or concentration.", examples=["Computer Science"])
    university: str | None = Field(default=None, max_length=200, description="School or university name.", examples=["The University of Alabama in Huntsville"])
    grad_year: str | None = Field(default=None, max_length=20, description="Graduation year or expected graduation year.", examples=["2026"])
    gpa: str | None = Field(default=None, max_length=20, description="Grade point average as free text.", examples=["3.84"])
    years_experience: str | None = Field(default=None, max_length=40, description="Total years of relevant professional experience.", examples=["5"])
    job_title: str | None = Field(default=None, max_length=160, description="Target role or current title used when autofilling applications.", examples=["Software Engineer"])
    skills_text: str | None = Field(default=None, max_length=6000, description="Comma-separated or paragraph-form list of technical and soft skills.", examples=["Python, FastAPI, PostgreSQL, Docker, AWS"])
    certifications_text: str | None = Field(default=None, max_length=6000, description="Professional certifications and credentials.", examples=["AWS Certified Developer - Associate (2025)"])
    professional_links_text: str | None = Field(default=None, max_length=6000, description="Additional professional links not captured in dedicated URL fields.", examples=["GitHub: https://github.com/janedoe; Medium: https://medium.com/@janedoe"])
    education_history_text: str | None = Field(default=None, max_length=12000, description="Detailed education history block used for longer application forms.", examples=["B.S. Computer Science, UAH, 2022-2026, GPA 3.84"])
    employment_history_text: str | None = Field(default=None, max_length=20000, description="Detailed employment history used for autofill and resume generation.", examples=["Software Engineer Intern, Acme Corp (Summer 2025): built API endpoints and dashboards."])
    demographic_gender: str | None = Field(default=None, max_length=80, description="Optional self-identified gender for EEO forms.", examples=["Prefer not to say"])
    demographic_ethnicity: str | None = Field(default=None, max_length=120, description="Optional self-identified ethnicity for EEO forms.", examples=["Prefer not to say"])
    veteran_status: str | None = Field(default=None, max_length=120, description="Optional veteran status answer used in compliance forms.", examples=["Not a protected veteran"])
    disability_status: str | None = Field(default=None, max_length=160, description="Optional disability self-identification response.", examples=["I do not wish to answer"])
    california_resident: str | None = Field(default=None, max_length=60, description="Optional California residency declaration used by some employers.", examples=["No"])

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return require_valid_email(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return normalize_phone(value)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    name: str | None = Field(
        default=None,
        max_length=120,
        description="Optional replacement profile name; if omitted, current name is preserved.",
        examples=["Data Science Profile"],
    )


class ProfileResponse(ProfileBase):
    id: int = Field(..., description="Unique identifier of this applicant profile.", examples=[15])
    user_id: int = Field(..., description="Owner user identifier.", examples=[42])
    is_active: bool = Field(..., description="True if this is the currently selected default profile for autofill operations.", examples=[True])
    created_at: datetime = Field(..., description="UTC timestamp when this profile was created.", examples=["2026-03-31T13:45:01.120000Z"])
    updated_at: datetime = Field(..., description="UTC timestamp of the most recent profile change.", examples=["2026-03-31T14:10:40.550000Z"])

    class Config:
        from_attributes = True


class ProfileListItem(BaseModel):
    id: int = Field(..., description="Profile identifier for selection or navigation.", examples=[15])
    name: str = Field(..., description="Profile display name in list and dropdown views.", examples=["Default"])
    is_active: bool = Field(..., description="Whether this profile is currently active for autofill operations.", examples=[False])
    first_name: str | None = Field(default=None, description="Applicant first name snapshot for quick list display.", examples=["Jane"])
    last_name: str | None = Field(default=None, description="Applicant last name snapshot for quick list display.", examples=["Doe"])
    created_at: datetime = Field(..., description="UTC timestamp when this profile was first created.", examples=["2026-03-31T13:45:01.120000Z"])

    class Config:
        from_attributes = True
