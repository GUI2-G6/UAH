"""Forward-looking scraper scaffold for ethical provider integrations."""

from __future__ import annotations

try:
    from app.scrapers.base.BaseProviderAdapter import BaseProviderAdapter, ProviderOptedOutError
    from app.scrapers.registry import (
        get_active_providers,
        get_all_providers,
        get_opted_out_providers,
        get_provider,
        register_provider,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - repo-root module execution fallback
    if exc.name != "app":
        raise
    from backend.app.scrapers.base.BaseProviderAdapter import BaseProviderAdapter, ProviderOptedOutError
    from backend.app.scrapers.registry import (
        get_active_providers,
        get_all_providers,
        get_opted_out_providers,
        get_provider,
        register_provider,
    )

__all__ = [
    "BaseProviderAdapter",
    "ProviderOptedOutError",
    "get_active_providers",
    "get_all_providers",
    "get_opted_out_providers",
    "get_provider",
    "register_provider",
]
