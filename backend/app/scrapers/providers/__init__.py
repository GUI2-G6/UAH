"""Scaffold providers only; live production examples remain in backend/app/providers/."""

from __future__ import annotations

try:
    from app.scrapers.providers.compat_dummy_provider import DUMMY_PENDING_MESSAGE, DummyProviderAdapter
except ModuleNotFoundError as exc:  # pragma: no cover - repo-root module execution fallback
    if exc.name != "app":
        raise
    from backend.app.scrapers.providers.compat_dummy_provider import DUMMY_PENDING_MESSAGE, DummyProviderAdapter

__all__ = ["DUMMY_PENDING_MESSAGE", "DummyProviderAdapter"]
