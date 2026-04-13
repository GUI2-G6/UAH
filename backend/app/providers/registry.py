from __future__ import annotations

from app.providers.base import JobProvider
from app.providers.the_muse import TheMuseJobProvider

_REGISTERED_PROVIDERS: dict[str, type[JobProvider]] = {
    "the_muse": TheMuseJobProvider,
}


def get_adapter(provider_name: str) -> JobProvider:
    """Return a provider adapter instance for the requested provider."""
    normalized = (provider_name or "").strip().lower()
    provider_cls = _REGISTERED_PROVIDERS.get(normalized)
    if provider_cls is None:
        raise ValueError(f"Unsupported job provider '{provider_name}'")
    # TODO: If UAH adds pluggable providers later, load adapters from a registry/config module here.
    return provider_cls()
