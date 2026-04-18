from datetime import datetime

from pydantic import BaseModel, Field


class InviteCreate(BaseModel):
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration timestamp after which the invite code is no longer redeemable.",
    )


class InviteBatchCreate(BaseModel):
    count: int = Field(
        ...,
        ge=1,
        le=50,
        description="Number of invite codes to generate in one request.",
        examples=[10],
    )
    expires_at: datetime | None = Field(
        default=None,
        description="Optional expiration timestamp applied to every generated invite in the batch.",
    )


class InviteResponse(BaseModel):
    id: int
    code: str
    created_by: int
    used_by: int | None = None
    used_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
