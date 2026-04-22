from pydantic import BaseModel, Field, field_validator

from app.core.validation import require_valid_email


class BetaAccessRequestCreate(BaseModel):
    email: str = Field(
        ...,
        description="Email address where beta onboarding follow-up should be sent.",
        examples=["person@example.com"],
    )
    full_name: str | None = Field(
        default=None,
        max_length=120,
        description="Optional full name for review context.",
        examples=["Jane Doe"],
    )
    notes: str | None = Field(
        default=None,
        max_length=1200,
        description="Optional details about job-search context or requested features.",
        examples=["Career switch from finance to data analytics."],
    )
    source_surface: str | None = Field(
        default=None,
        max_length=64,
        description="Optional source identifier for where the request was submitted.",
        examples=["landing_beta_access"],
    )

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return require_valid_email(value, field_name="email")

    @field_validator("full_name", "notes", "source_surface")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class BetaAccessRequestResponse(BaseModel):
    message: str = Field(
        ...,
        description="Neutral acknowledgment message for beta access requests.",
        examples=["Thanks - your beta access request has been received."],
    )
