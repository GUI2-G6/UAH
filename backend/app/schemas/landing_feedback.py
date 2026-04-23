from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.core.validation import require_valid_email


class LandingFeedbackCreate(BaseModel):
    email: str = Field(
        ...,
        description="Contact email for follow-up.",
        examples=["person@example.com"],
    )
    full_name: str | None = Field(
        default=None,
        max_length=120,
        description="Optional display name.",
        examples=["Jane Doe"],
    )
    frustration: str | None = Field(
        default=None,
        max_length=8000,
        description="What frustrates the submitter about job search.",
    )
    features: str | None = Field(
        default=None,
        max_length=8000,
        description="Desired capabilities in a job search tool.",
    )
    notify_public: bool = Field(default=False, description="Notify when public access opens.")
    interested_beta: bool = Field(default=False, description="Interested in beta access.")
    source_surface: str | None = Field(
        default=None,
        max_length=64,
        description="Where the submission was sent from.",
        examples=["landing_wishlist"],
    )

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        return require_valid_email(value, field_name="email")

    @field_validator("full_name", "frustration", "features", "source_surface")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class LandingFeedbackResponse(BaseModel):
    message: str = Field(
        ...,
        description="Acknowledgment that the feedback was stored.",
        examples=["Thanks — we received your feedback."],
    )
