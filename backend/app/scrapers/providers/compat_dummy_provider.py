"""Compatibility wrapper for the neutral dummy scaffold adapter."""

from __future__ import annotations

try:
    from app.scrapers.providers.dummy_provider import DUMMY_PENDING_MESSAGE, DummyProviderAdapter
except ModuleNotFoundError as exc:  # pragma: no cover - repo-root module execution fallback
    if exc.name != "app":
        raise
    from backend.app.scrapers.providers.dummy_provider import DUMMY_PENDING_MESSAGE, DummyProviderAdapter

__all__ = ["DUMMY_PENDING_MESSAGE", "DummyProviderAdapter"]
