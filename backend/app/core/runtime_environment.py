"""Helpers for runtime environment decisions that need fail-closed behavior."""

from __future__ import annotations


def generated_docs_enabled(raw_environment: str | None) -> bool:
    """Only expose generated API docs for explicit local/dev environments."""

    environment = (raw_environment or "").strip().lower()
    return environment in {"development", "dev", "local"}
