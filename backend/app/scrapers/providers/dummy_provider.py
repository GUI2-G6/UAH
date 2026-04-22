"""Stub adapter for the pending dummy scaffold integration."""

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

DUMMY_PENDING_MESSAGE = (
    "Dummy provider integration pending for scaffold validation. "
    "Implement adapter logic after provider review is complete."
)


class DummyProviderAdapter(BaseProviderAdapter):
    """Stub scaffold adapter used as a neutral provider placeholder."""

    def get_provider_name(self) -> str:
        """Return the human-readable provider name."""
        return "Dummy Provider"

    def get_base_url(self) -> str:
        """Return the base provider domain for robots and opt-out checks."""
        return "https://example.com"

    def get_user_agent(self) -> str:
        """Return UAH's descriptive scraper user agent."""
        return super().get_user_agent()

    def get_rate_limit_seconds(self) -> float:
        """Return the default request pacing for the pending integration."""
        return 2.0

    def fetch_listings(self, query: str | None, location: str | None, page: int) -> list[dict[str, Any]]:
        """Raise pending status until this placeholder adapter is implemented."""
        del query, location, page
        raise NotImplementedError(DUMMY_PENDING_MESSAGE)

    def normalize_listing(self, raw: dict[str, Any]) -> NormalizedJob:
        """Raise pending status until this placeholder adapter is implemented."""
        del raw
        raise NotImplementedError(DUMMY_PENDING_MESSAGE)

    def is_active(self) -> bool:
        """Return False until the placeholder adapter is implemented and reviewed."""
        return False


__all__ = ["DUMMY_PENDING_MESSAGE", "DummyProviderAdapter"]
