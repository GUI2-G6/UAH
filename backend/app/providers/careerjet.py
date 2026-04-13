from __future__ import annotations

from app.providers.base import JobProvider
from app.schemas.job import NormalizedJob

PROVIDER_NOTES = """
Careerjet is intentionally dormant in UAH.
- Careerjet's API is designed around pay-per-click monetization and real user traffic.
- Requests require end-user `user_ip` and `user_agent`, which conflicts with UAH's autonomous background ingest model.
- The API does not provide a stable job id; URLs must be used as identifiers.
- Descriptions are excerpt-only and controlled by `fragment_size`.
- This mismatch is architectural, not a missing attribution or quota detail.
"""


class CareerjetJobProvider(JobProvider):
    """Disabled stub for Careerjet until UAH adopts a request-per-user model."""

    @property
    def provider_name(self) -> str:
        return "careerjet"

    @property
    def max_page_size(self) -> int:
        return 20

    @property
    def rate_limit_per_hour(self) -> int:
        return 1

    def map_filters(self, internal_filters: dict) -> dict:
        """Return the passthrough filter payload for the disabled stub."""
        return dict(internal_filters or {})

    def fetch(self, params: dict) -> list[NormalizedJob]:
        """Raise an explanatory error because this provider is intentionally unsupported."""
        raise NotImplementedError(
            "Careerjet is disabled because its API requires real end-user IP/user-agent context and a PPC traffic model "
            "that conflicts with UAH's background local-cache ingest architecture."
        )
