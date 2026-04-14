from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.providers.base import JobProvider
from app.providers.common import (
    clean_html_text,
    infer_remote_flag,
    normalize_experience_level,
    normalize_job_type,
    normalize_provider_categories,
    parse_iso_datetime_with_trimmed_fraction,
)
from app.schemas.job import NormalizedJob
from app.services.provider_requests import ProviderRequestFailed, tracked_request

PROVIDER_NOTES = """
Jooble API
- Auth uses the API key in the request path and requires POST + JSON body.
- Job ids can be large negative integers, so UAH stores them as strings.
- `updated` is the only stable freshness timestamp returned by Jooble, so UAH uses it as the normalized posting date.
- `link` is usually a Jooble redirect wrapper, not the downstream employer apply URL.
- Jooble heavily re-aggregates third-party boards, so cross-provider deduplication is especially important.
"""


class JoobleJobProvider(JobProvider):
    """Provider adapter for the Jooble jobs API."""

    @property
    def provider_name(self) -> str:
        return "jooble"

    @property
    def max_page_size(self) -> int:
        return max(int(settings.JOOBLE_PAGE_SIZE), 1)

    @property
    def rate_limit_per_hour(self) -> int:
        delay_seconds = max(float(settings.JOOBLE_INTER_REQUEST_DELAY), 0.1)
        return max(int(3600 / delay_seconds), 1)

    def map_filters(self, internal_filters: dict) -> dict:
        """Convert canonical UAH filters into a Jooble POST body."""
        payload: dict[str, Any] = {
            "page": max(int(internal_filters.get("page") or 1), 1),
            "ResultOnPage": self.max_page_size,
        }
        keywords = " ".join(str(internal_filters.get("keywords") or "").split())
        if keywords:
            payload["keywords"] = keywords
        location = " ".join(str(internal_filters.get("location") or "").split())
        if location:
            payload["location"] = location
        radius = " ".join(str(internal_filters.get("radius") or "").split())
        if radius:
            payload["radius"] = radius
        salary = internal_filters.get("salary")
        if salary not in {None, ""}:
            payload["salary"] = int(salary)
        if internal_filters.get("companysearch") is True:
            payload["companysearch"] = "true"
        return payload

    def fetch(self, params: dict) -> list[NormalizedJob]:
        """Fetch one page from Jooble and normalize the response."""
        api_key = (settings.JOOBLE_API_KEY or "").strip()
        if not api_key:
            raise ProviderRequestFailed("Jooble API key is not configured.")

        response = tracked_request(
            provider_name=self.provider_name,
            rate_limit_per_hour=self.rate_limit_per_hour,
            method="POST",
            url=f"https://jooble.org/api/{api_key}",
            json_body=self.map_filters(params),
            timeout_seconds=20.0,
        )
        if response.status_code != 200:
            raise ProviderRequestFailed(
                f"Jooble request failed with status {response.status_code}: {response.text[:200]}"
            )

        payload = response.json()
        raw_jobs = payload.get("jobs") if isinstance(payload, dict) else payload
        if not isinstance(raw_jobs, list):
            return []

        normalized: list[NormalizedJob] = []
        for item in raw_jobs:
            title = " ".join(str(item.get("title") or "").split())
            company = " ".join(str(item.get("company") or "").split()) or None
            location = " ".join(str(item.get("location") or "").split()) or None
            description = clean_html_text(item.get("snippet"))
            source = " ".join(str(item.get("source") or "").split()).lower()
            type_value = " ".join(str(item.get("type") or "").split()) or None
            source_tags = ["provider:jooble", "source:jooble_api"]
            if source:
                source_tags.append(f"upstream_source:{source}")

            normalized.append(
                NormalizedJob(
                    provider=self.provider_name,
                    provider_job_id=str(item.get("id")),
                    provider_url=" ".join(str(item.get("link") or "").split()) or None,
                    title=title,
                    company=company,
                    location=location,
                    is_remote=infer_remote_flag(title=title, location=location, description=description),
                    job_type=normalize_job_type([type_value] if type_value else []),
                    experience_level=normalize_experience_level(title=title),
                    categories=normalize_provider_categories(values=[type_value or "", source], title=title, description=description),
                    description=description,
                    published_at=parse_iso_datetime_with_trimmed_fraction(item.get("updated")),
                    source_tags=source_tags,
                )
            )

        return normalized
