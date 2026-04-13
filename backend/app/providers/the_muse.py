from __future__ import annotations

from datetime import datetime, timezone
import html
import re
from typing import Any

from app.api.routes import _expand_category_for_muse
from app.core.config import settings
from app.providers.base import JobProvider
from app.schemas.job import NormalizedJob
from app.services.provider_requests import ProviderRequestFailed, tracked_request

MUSE_BASE_URL = "https://www.themuse.com/api/public/jobs"
_TAG_RE = re.compile(r"<[^>]+>")
_REMOTE_RE = re.compile(r"\b(remote|work from home|telecommute|distributed|anywhere)\b", re.IGNORECASE)

_MUSE_LEVEL_MAP = {
    "internship": "internship",
    "entry level": "entry",
    "mid level": "mid",
    "senior level": "senior",
    "management": "manager",
    "manager": "manager",
    "director": "director",
    "vp": "vp",
}

_UAH_TO_MUSE_LEVEL_QUERY = {
    "internship": "Internship",
    "entry": "Entry Level",
    "entry level": "Entry Level",
    "mid": "Mid Level",
    "mid level": "Mid Level",
    "senior": "Senior Level",
    "senior level": "Senior Level",
    "manager": "Management",
    "management": "Management",
    "director": "Director",
    "vp": "VP",
}


def _clean_html_text(value: str | None) -> str:
    plain = _TAG_RE.sub(" ", value or "")
    plain = html.unescape(plain)
    return " ".join(plain.split())


def _parse_publication_date(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _map_experience_level(levels: list[dict[str, Any]] | None) -> str | None:
    for level in levels or []:
        raw = " ".join(str(level.get("name") or "").strip().lower().split())
        if raw in _MUSE_LEVEL_MAP:
            return _MUSE_LEVEL_MAP[raw]
    return None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = " ".join((value or "").split())
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


class TheMuseJobProvider(JobProvider):
    """Provider adapter for The Muse public jobs API."""

    @property
    def provider_name(self) -> str:
        return "the_muse"

    @property
    def max_page_size(self) -> int:
        return 20

    @property
    def rate_limit_per_hour(self) -> int:
        return max(int(settings.THE_MUSE_RATE_LIMIT_PER_HOUR), 1)

    def map_filters(self, internal_filters: dict) -> dict:
        """Convert canonical UAH filters into Muse API params."""
        params: dict[str, Any] = {}

        categories = []
        for category in internal_filters.get("category") or []:
            categories.extend(_expand_category_for_muse(category))
        if categories:
            params["category"] = _dedupe(categories)

        locations = _dedupe(list(internal_filters.get("location") or []))
        if locations:
            params["location"] = locations

        levels = []
        for value in internal_filters.get("experience_level") or []:
            normalized = _UAH_TO_MUSE_LEVEL_QUERY.get(" ".join(str(value).strip().lower().split()))
            if normalized:
                levels.append(normalized)
        if levels:
            params["level"] = _dedupe(levels)

        # TODO: Add provider-native remote filtering when a future provider supports it directly.
        if internal_filters.get("page") is not None:
            params["page"] = int(internal_filters["page"])

        if settings.THE_MUSE_API_KEY:
            params["api_key"] = settings.THE_MUSE_API_KEY

        return params

    def fetch(self, params: dict) -> list[NormalizedJob]:
        """Fetch one page from The Muse and normalize each returned posting."""
        provider_params = self.map_filters(params)
        response = tracked_request(
            provider_name=self.provider_name,
            rate_limit_per_hour=self.rate_limit_per_hour,
            method="GET",
            url=MUSE_BASE_URL,
            params=provider_params,
            timeout_seconds=15.0,
        )
        if response.status_code != 200:
            raise ProviderRequestFailed(
                f"The Muse request failed with status {response.status_code}: {response.text[:200]}"
            )

        payload = response.json()
        results = payload.get("results") or []
        normalized: list[NormalizedJob] = []
        for item in results:
            company = item.get("company") or {}
            location_values = [loc.get("name") for loc in item.get("locations") or [] if loc.get("name")]
            description_text = _clean_html_text(item.get("contents"))
            categories = _dedupe([cat.get("name") for cat in item.get("categories") or [] if cat.get("name")])
            is_remote = any(_REMOTE_RE.search(value or "") for value in location_values)
            if not is_remote and _REMOTE_RE.search(description_text):
                is_remote = True

            normalized.append(
                NormalizedJob(
                    provider=self.provider_name,
                    provider_job_id=str(item.get("id")),
                    provider_url=(item.get("refs") or {}).get("landing_page"),
                    title=(item.get("name") or "").strip(),
                    company=(company.get("name") or "").strip() or None,
                    company_url=(company.get("href") or "").strip() or None,
                    location=location_values[0] if location_values else None,
                    is_remote=is_remote,
                    job_type=(item.get("type") or "").strip() or None,
                    experience_level=_map_experience_level(item.get("levels")),
                    categories=categories,
                    description=description_text,
                    published_at=_parse_publication_date(item.get("publication_date")),
                )
            )

        return normalized
