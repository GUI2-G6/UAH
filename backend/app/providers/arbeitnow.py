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
    parse_unix_timestamp,
)
from app.schemas.job import NormalizedJob
from app.services.provider_requests import ProviderRequestFailed, tracked_request

ARBEITNOW_BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

PROVIDER_NOTES = """
Arbeitnow job board API
- No authentication required.
- The API tolerates light automation, but Cloudflare blocks rapid bursts; UAH enforces a 3-second minimum page pace via the configured hourly rate.
- `remote=true` and `visa_sponsorship=true` are not trustworthy at the API edge, so remote/visa filters are post-filtered after the response.
- `slug` is the stable provider job id.
- `created_at` is a unix timestamp.
- `url` is usually a direct ATS link, so UAH stores it as both provider_url and apply_url.
"""


class ArbeitnowJobProvider(JobProvider):
    """Provider adapter for the Arbeitnow job board API."""

    @property
    def provider_name(self) -> str:
        return "arbeitnow"

    @property
    def max_page_size(self) -> int:
        return 100

    @property
    def rate_limit_per_hour(self) -> int:
        delay_seconds = max(float(settings.ARBEITNOW_INTER_REQUEST_DELAY), 0.1)
        return max(int(3600 / delay_seconds), 1)

    def map_filters(self, internal_filters: dict) -> dict:
        """Convert canonical UAH filters into Arbeitnow API params."""
        params: dict[str, Any] = {
            # Passing explicit params avoids the default country-scoped feed behavior.
            "page": max(int(internal_filters.get("page") or 1), 1),
        }

        if internal_filters.get("is_remote") is True:
            params["remote"] = True
        if internal_filters.get("visa_sponsorship") is True:
            params["visa_sponsorship"] = True
        return params

    def fetch(self, params: dict) -> list[NormalizedJob]:
        """Fetch one page from Arbeitnow and normalize it for ingest."""
        provider_params = self.map_filters(params)
        response = tracked_request(
            provider_name=self.provider_name,
            rate_limit_per_hour=self.rate_limit_per_hour,
            method="GET",
            url=ARBEITNOW_BASE_URL,
            params=provider_params,
            timeout_seconds=20.0,
        )
        if response.status_code != 200:
            raise ProviderRequestFailed(
                f"Arbeitnow request failed with status {response.status_code}: {response.text[:200]}"
            )

        payload = response.json()
        raw_jobs = payload.get("data") if isinstance(payload, dict) else payload
        if not isinstance(raw_jobs, list):
            return []

        if params.get("is_remote") is True:
            raw_jobs = [job for job in raw_jobs if job.get("remote") is True]
        if params.get("visa_sponsorship") is True:
            raw_jobs = [job for job in raw_jobs if job.get("visa_sponsorship") is True]

        normalized: list[NormalizedJob] = []
        for item in raw_jobs:
            title = " ".join(str(item.get("title") or "").split())
            company = " ".join(str(item.get("company_name") or "").split()) or None
            location = " ".join(str(item.get("location") or "").split()) or None
            description = clean_html_text(item.get("description"))
            job_types = dedupe_strings([str(value) for value in (item.get("job_types") or []) if value])
            tags = dedupe_strings([str(value) for value in (item.get("tags") or []) if value])
            provider_url = " ".join(str(item.get("url") or "").split()) or None

            normalized.append(
                NormalizedJob(
                    provider=self.provider_name,
                    provider_job_id=" ".join(str(item.get("slug") or "").split()),
                    provider_url=provider_url,
                    apply_url=provider_url,
                    title=title,
                    company=company,
                    location=location,
                    is_remote=bool(item.get("remote") is True),
                    job_type=normalize_job_type(job_types),
                    experience_level=normalize_experience_level(values=job_types + tags, title=title),
                    categories=normalize_provider_categories(values=job_types + tags, title=title, description=description),
                    description=description,
                    published_at=parse_unix_timestamp(item.get("created_at")),
                    source_tags=["provider:arbeitnow", "source:arbeitnow_api"],
                )
            )

        return normalized
