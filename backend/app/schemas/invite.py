from datetime import datetime

from pydantic import BaseModel, Field


class InviteCreate(BaseModel):
    name: str | None = Field(
        default=None,
        max_length=120,
        description="Optional human-friendly label for the invite code.",
    )
    max_uses: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Maximum number of successful redemptions before the invite becomes invalid.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration timestamp after which the invite code is no longer redeemable.",
    )
    expires_in: str | None = Field(
        default=None,
        description="Optional relative duration (example: 1w, 1hr, 30min, 1m, 1y).",
    )


class InviteBatchCreate(BaseModel):
    count: int = Field(
        ...,
        ge=1,
        le=50,
        description="Number of invite codes to generate in one request.",
        examples=[10],
    )
    name: str | None = Field(
        default=None,
        max_length=120,
        description="Optional human-friendly label applied to every generated invite.",
    )
    max_uses: int = Field(
        default=1,
        ge=1,
        le=10000,
        description="Maximum number of successful redemptions allowed per invite.",
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration timestamp applied to every generated invite in the batch.",
    )
    expires_in: str | None = Field(
        default=None,
        description="Optional relative duration (example: 1w, 1hr, 30min, 1m, 1y).",
    )


class InviteResponse(BaseModel):
    id: int
    code: str
    name: str | None = None
    created_by: int
    max_uses: int
    use_count: int
    used_by: int | None = None
    used_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
