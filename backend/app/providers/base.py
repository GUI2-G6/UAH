from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas.job import NormalizedJob


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
