"""Stub adapter for the pending WhatJobs integration."""

from __future__ import annotations

from typing import Any

try:
    from app.schemas.job import NormalizedJob
    from app.scrapers.base.BaseProviderAdapter import BaseProviderAdapter
except ModuleNotFoundError as exc:  # pragma: no cover - repo-root module execution fallback
    if exc.name != "app":
        raise
    from backend.app.schemas.job import NormalizedJob
    from backend.app.scrapers.base.BaseProviderAdapter import BaseProviderAdapter

WHATJOBS_PENDING_MESSAGE = (
    "WhatJobs integration pending — FeedAPI partnership in progress. "
    "See docs/WhatJobs-partnership.md when ready to implement."
)


class WhatJobsAdapter(BaseProviderAdapter):
    """Stub scaffold for WhatJobs until the partnership workflow is ready."""

    def get_provider_name(self) -> str:
        """Return the human-readable provider name."""
        return "WhatJobs"

    def get_base_url(self) -> str:
        """Return the base provider domain for robots and opt-out checks."""
        return "https://www.whatjobs.com"

    def get_user_agent(self) -> str:
        """Return UAH's descriptive scraper user agent."""
        return super().get_user_agent()

    def get_rate_limit_seconds(self) -> float:
        """Return the default request pacing for the pending integration."""
        return 2.0

    def fetch_listings(self, query: str | None, location: str | None, page: int) -> list[dict[str, Any]]:
        """WhatJobs integration pending — FeedAPI partnership in progress. See docs/WhatJobs-partnership.md when ready to implement."""
        del query, location, page
        raise NotImplementedError(WHATJOBS_PENDING_MESSAGE)

    def normalize_listing(self, raw: dict[str, Any]) -> NormalizedJob:
        """WhatJobs integration pending — FeedAPI partnership in progress. See docs/WhatJobs-partnership.md when ready to implement."""
        del raw
        raise NotImplementedError(WHATJOBS_PENDING_MESSAGE)

    def is_active(self) -> bool:
        """Return False until the WhatJobs integration is implemented and reviewed."""
        return False


__all__ = ["WHATJOBS_PENDING_MESSAGE", "WhatJobsAdapter"]
