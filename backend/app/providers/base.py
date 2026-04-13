from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.schemas.job import NormalizedJob
from app.services.job_link_health import classify_apply_portal, classify_job_url_validation_verdict


class JobProvider(ABC):
    """Abstract adapter for a single upstream jobs provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Stable provider identifier used throughout the jobs subsystem."""

    @property
    @abstractmethod
    def max_page_size(self) -> int:
        """Maximum number of rows the provider returns per page request."""

    @property
    @abstractmethod
    def rate_limit_per_hour(self) -> int:
        """Provider-specific outbound request budget for one rolling hour."""

    @abstractmethod
    def fetch(self, params: dict) -> list[NormalizedJob]:
        """Fetch one page of provider results and normalize them for ingest."""

    @abstractmethod
    def map_filters(self, internal_filters: dict) -> dict:
        """Convert UAH filter keys into provider-specific request params."""

    def classify_landing_page_verdict(self, *, url: str | None, status_code: int, body_text: str | None) -> str:
        """Classify one provider landing-page response as good, bad, or unknown."""
        return classify_job_url_validation_verdict(status_code, body_text)

    def resolve_apply_details(
        self,
        *,
        landing_url: str | None,
        final_url: str | None,
        body_text: str | None,
    ) -> dict[str, Any]:
        """Return apply-link details derived from a provider landing page."""
        return {
            "apply_url": None,
            "apply_host": None,
            "apply_portal": "missing",
        }

    def classify_apply_portal(self, apply_url: str | None) -> str:
        """Return a canonical portal slug for one downstream apply URL."""
        return classify_apply_portal(apply_url)
