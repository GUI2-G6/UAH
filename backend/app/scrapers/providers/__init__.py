"""Scaffold providers only; live production examples remain in backend/app/providers/."""

from __future__ import annotations

try:
    from app.scrapers.providers.WhatJobs import WhatJobsAdapter
except ModuleNotFoundError as exc:  # pragma: no cover - repo-root module execution fallback
    if exc.name != "app":
        raise
    from backend.app.scrapers.providers.WhatJobs import WhatJobsAdapter

__all__ = ["WhatJobsAdapter"]
