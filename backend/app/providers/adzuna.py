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
    parse_iso_datetime,
)
from app.schemas.job import NormalizedJob
from app.services.provider_requests import ProviderQuotaExceeded, ProviderRequestFailed, confirm_request_budget, tracked_request

PROVIDER_NOTES = """
Adzuna API
- Auth uses `app_id` and `app_key` query params.
- Hourly pacing is governed by the provider's hard 25 requests/minute limit.
- Background use must stop once UAH reaches its configured daily request budget.
- Descriptions are snippet-length only and `redirect_url` is an Adzuna wrapper, not the direct employer apply page.
- Salary data is mostly predicted; UAH does not surface salary-specific fields in this rollout.
"""


class AdzunaJobProvider(JobProvider):
    """Provider adapter for the Adzuna jobs API."""

    @property
    def provider_name(self) -> str:
        return "adzuna"

    @property
    def max_page_size(self) -> int:
        return 20

    @property
    def rate_limit_per_hour(self) -> int:
        return 1500

    def map_filters(self, internal_filters: dict) -> dict:
        """Convert canonical UAH filters into Adzuna search params."""
        params: dict[str, Any] = {
            "app_id": settings.ADZUNA_APP_ID,
            "app_key": settings.ADZUNA_APP_KEY,
            "results_per_page": self.max_page_size,
        }
        category = " ".join(str((internal_filters.get("category") or [None])[0] or "").split())
        if category:
            params["what"] = category
        location = " ".join(str((internal_filters.get("location") or [None])[0] or "").split())
        if location:
            params["where"] = location
        return params

    def fetch(self, params: dict) -> list[NormalizedJob]:
        """Fetch one Adzuna result page and normalize the payload."""
        if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
            raise ProviderRequestFailed("Adzuna credentials are not configured.")
        if not confirm_request_budget(
            provider_name=self.provider_name,
            rate_limit_per_hour=self.rate_limit_per_hour,
            daily_request_budget=max(int(settings.ADZUNA_DAILY_REQUEST_BUDGET), 1),
        ):
            raise ProviderQuotaExceeded("Adzuna daily request budget has been exhausted for background sync.")

        page = max(int(params.get("page") or 1), 1)
        response = tracked_request(
            provider_name=self.provider_name,
            rate_limit_per_hour=self.rate_limit_per_hour,
            daily_request_budget=max(int(settings.ADZUNA_DAILY_REQUEST_BUDGET), 1),
            method="GET",
            url=f"https://api.adzuna.com/v1/api/jobs/us/search/{page}",
            params=self.map_filters(params),
            timeout_seconds=20.0,
        )
        if response.status_code != 200:
            raise ProviderRequestFailed(
                f"Adzuna request failed with status {response.status_code}: {response.text[:200]}"
            )

        payload = response.json()
        raw_jobs = payload.get("results") if isinstance(payload, dict) else payload
        if not isinstance(raw_jobs, list):
            return []

        normalized: list[NormalizedJob] = []
        for item in raw_jobs:
            title = " ".join(str(item.get("title") or "").split())
            company = " ".join(str((item.get("company") or {}).get("display_name") or "").split()) or None
            location = " ".join(str((item.get("location") or {}).get("display_name") or "").split()) or None
            description = clean_html_text(item.get("description"))
            category_label = " ".join(str((item.get("category") or {}).get("label") or "").split())

            normalized.append(
                NormalizedJob(
                    provider=self.provider_name,
                    provider_job_id=str(item.get("id")),
                    provider_url=" ".join(str(item.get("redirect_url") or "").split()) or None,
                    title=title,
                    company=company,
                    location=location,
                    is_remote=infer_remote_flag(title=title, location=location, description=description),
                    job_type=normalize_job_type([str(item.get("contract_type") or ""), str(item.get("contract_time") or "")]),
                    experience_level=normalize_experience_level(title=title),
                    categories=normalize_provider_categories(values=[category_label], title=title, description=description),
                    description=description,
                    published_at=parse_iso_datetime(item.get("created")),
                    source_tags=["provider:adzuna", "source:adzuna_api"],
                )
            )

        return normalized
