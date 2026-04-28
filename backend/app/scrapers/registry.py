"""Scaffold-native registry for future scraper adapters."""

from __future__ import annotations

from typing import Iterable

try:
    from app.scrapers.base.BaseProviderAdapter import BaseProviderAdapter
    from app.scrapers.providers import DummyProviderAdapter
except ModuleNotFoundError as exc:  # pragma: no cover - repo-root module execution fallback
    if exc.name != "app":
        raise
    from backend.app.scrapers.base.BaseProviderAdapter import BaseProviderAdapter
    from backend.app.scrapers.providers import DummyProviderAdapter

_REGISTERED_PROVIDERS: dict[str, BaseProviderAdapter] = {}


def _normalize_provider_name(name: str) -> str:
    """Return a normalized provider-name lookup key."""
    return " ".join((name or "").strip().lower().split())


def register_provider(adapter_instance: BaseProviderAdapter) -> BaseProviderAdapter:
    """Register a new scaffold adapter instance."""
    key = _normalize_provider_name(adapter_instance.get_provider_name())
    if not key:
        raise ValueError("adapter_instance must provide a non-empty provider name")
    _REGISTERED_PROVIDERS[key] = adapter_instance
    return adapter_instance


def _sorted_providers(values: Iterable[BaseProviderAdapter]) -> list[BaseProviderAdapter]:
    """Return adapters sorted by provider name for stable iteration."""
    return sorted(values, key=lambda adapter: _normalize_provider_name(adapter.get_provider_name()))


def get_all_providers() -> list[BaseProviderAdapter]:
    """Return all scaffold-native registered adapters."""
    return _sorted_providers(_REGISTERED_PROVIDERS.values())


def get_active_providers() -> list[BaseProviderAdapter]:
    """Return scaffold adapters that currently pass robots and opt-out checks."""
    active: list[BaseProviderAdapter] = []
    for adapter in get_all_providers():
        try:
            if adapter.is_active():
                active.append(adapter)
        except Exception:
            continue
    return active


def get_provider(name: str) -> BaseProviderAdapter:
    """Return one scaffold adapter by provider name."""
    key = _normalize_provider_name(name)
    adapter = _REGISTERED_PROVIDERS.get(key)
    if adapter is None:
        raise ValueError(f"Unsupported scraper provider '{name}'")
    return adapter


def get_opted_out_providers() -> list[BaseProviderAdapter]:
    """Return scaffold adapters present in the committed opt-out registry."""
    return [adapter for adapter in get_all_providers() if adapter.get_opt_out_status()]


register_provider(DummyProviderAdapter())

__all__ = [
    "get_active_providers",
    "get_all_providers",
    "get_opted_out_providers",
    "get_provider",
    "register_provider",
]
