from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.providers.base import JobProvider
from app.providers.common import (
    clean_html_text,
    dedupe_strings,
    normalize_experience_level,
    normalize_job_type,
    normalize_provider_categories,
    parse_iso_datetime,
)
from app.schemas.job import NormalizedJob
from app.services.provider_requests import ProviderRequestFailed, tracked_request

FINDWORK_BASE_URL = "https://findwork.dev/api/jobs/"

PROVIDER_NOTES = """
Findwork API
- Token auth via `Authorization: Token <key>`.
- Real-world throttling is stricter than the public docs; UAH uses a 6-second page pace.
- `id` is a short string slug, not a safe integer.
- `role` is the canonical job title field.
- `remote` is reliable and is used directly.
- `text` contains the full description.
- `source` identifies the upstream job board and is preserved in source_tags.
"""


class FindworkJobProvider(JobProvider):
    """Provider adapter for the Findwork jobs API."""

    @property
    def provider_name(self) -> str:
        return "findwork"

    @property
    def max_page_size(self) -> int:
        return 100

    @property
    def rate_limit_per_hour(self) -> int:
        delay_seconds = max(float(settings.FINDWORK_INTER_REQUEST_DELAY), 0.1)
        return max(int(3600 / delay_seconds), 1)

    def map_filters(self, internal_filters: dict) -> dict:
        """Convert canonical UAH filters into Findwork API params."""
        params: dict[str, Any] = {
            "page": max(int(internal_filters.get("page") or 1), 1),
        }
        if internal_filters.get("is_remote") is True:
            params["remote"] = True
        return params

    def fetch(self, params: dict) -> list[NormalizedJob]:
        """Fetch one page from Findwork and normalize the result set."""
        provider_params = self.map_filters(params)
        headers = {}
        if settings.FINDWORK_API_KEY:
            headers["Authorization"] = f"Token {settings.FINDWORK_API_KEY}"

        response = tracked_request(
            provider_name=self.provider_name,
            rate_limit_per_hour=self.rate_limit_per_hour,
            method="GET",
            url=FINDWORK_BASE_URL,
            params=provider_params,
            headers=headers or None,
            timeout_seconds=20.0,
        )
        if response.status_code != 200:
            raise ProviderRequestFailed(
                f"Findwork request failed with status {response.status_code}: {response.text[:200]}"
            )

        payload = response.json()
        raw_jobs = payload.get("results") if isinstance(payload, dict) else payload
        if not isinstance(raw_jobs, list):
            return []

        normalized: list[NormalizedJob] = []
        for item in raw_jobs:
            title = " ".join(str(item.get("role") or "").split())
            company = " ".join(str(item.get("company_name") or "").split()) or None
            location = " ".join(str(item.get("location") or "").split()) or None
            description = clean_html_text(item.get("text"))
            keywords = dedupe_strings([str(value) for value in (item.get("keywords") or []) if value])
            provider_url = " ".join(str(item.get("url") or "").split()) or None
            upstream_source = " ".join(str(item.get("source") or "").split()).lower()
            source_tags = ["provider:findwork", "source:findwork_api"]
            if upstream_source:
                source_tags.append(f"upstream_source:{upstream_source}")

            normalized.append(
                NormalizedJob(
                    provider=self.provider_name,
                    provider_job_id=" ".join(str(item.get("id") or "").split()),
                    provider_url=provider_url,
                    apply_url=provider_url,
                    title=title,
                    company=company,
                    location=location,
                    is_remote=bool(item.get("remote") is True),
                    job_type=normalize_job_type(item.get("employment_type") if isinstance(item.get("employment_type"), list) else None),
                    experience_level=normalize_experience_level(values=keywords, title=title),
                    categories=normalize_provider_categories(values=keywords, title=title, description=description),
                    description=description,
                    published_at=parse_iso_datetime(item.get("date_posted")),
                    source_tags=source_tags,
                )
            )

        return normalized
