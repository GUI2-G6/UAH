from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class NormalizedJob(BaseModel):
    """Provider-agnostic normalized job payload used by ingest logic."""

    provider: str = Field(..., min_length=1, max_length=50)
    provider_job_id: str = Field(..., min_length=1, max_length=255)
    provider_url: str | None = None
    apply_url: str | None = None
    apply_host: str | None = None
    apply_portal: str | None = None
    source_tags: list[str] = Field(default_factory=list)
    title: str
    company: str | None = None
    company_url: str | None = None
    location: str | None = None
    is_remote: bool = False
    job_type: str | None = None
    experience_level: str | None = None
    categories: list[str] = Field(default_factory=list)
    description: str | None = None
    published_at: datetime | None = None
