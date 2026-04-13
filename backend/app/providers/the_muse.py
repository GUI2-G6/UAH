from __future__ import annotations

from datetime import datetime, timezone
import html
from html.parser import HTMLParser
import re
from typing import Any
from urllib.parse import urljoin

from app.api.routes import _expand_category_for_muse
from app.core.config import settings
from app.providers.base import JobProvider
from app.schemas.job import NormalizedJob
from app.services.provider_requests import ProviderRequestFailed, tracked_request
from app.services.job_link_health import classify_job_url_validation_verdict, extract_url_host

MUSE_BASE_URL = "https://www.themuse.com/api/public/jobs"
_TAG_RE = re.compile(r"<[^>]+>")
_REMOTE_RE = re.compile(r"\b(remote|work from home|telecommute|distributed|anywhere)\b", re.IGNORECASE)
_MUSE_JOB_NOT_FOUND_PATTERNS = [
    re.compile(r"\bjob not found\b", re.IGNORECASE),
    re.compile(r"\bthe job posting you'?re looking for could not be found\b", re.IGNORECASE),
    re.compile(r"\bmay have been removed\b", re.IGNORECASE),
]
_APPLY_LINK_TEXT_RE = re.compile(r"\bapply on company site\b", re.IGNORECASE)

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


class _MuseApplyLinkParser(HTMLParser):
    """Capture the first anchor whose visible text looks like the apply CTA."""

    def __init__(self):
        super().__init__()
        self._current_href: str | None = None
        self._current_text_parts: list[str] = []
        self.apply_href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a" or self.apply_href is not None:
            return
        attr_map = {key.lower(): value for key, value in attrs}
        self._current_href = attr_map.get("href")
        self._current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_href is None or self.apply_href is not None:
            return
        if data:
            self._current_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current_href is None or self.apply_href is not None:
            self._current_href = None
            self._current_text_parts = []
            return

        text = " ".join(part.strip() for part in self._current_text_parts if part.strip())
        if _APPLY_LINK_TEXT_RE.search(text):
            self.apply_href = self._current_href

        self._current_href = None
        self._current_text_parts = []


def _extract_apply_on_company_site_url(body_text: str | None, base_url: str | None) -> str | None:
    parser = _MuseApplyLinkParser()
    parser.feed(body_text or "")
    parser.close()
    href = (parser.apply_href or "").strip()
    if not href:
        return None
    return urljoin(base_url or "", href)


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

    def classify_landing_page_verdict(self, *, url: str | None, status_code: int, body_text: str | None) -> str:
        """Classify Muse landing pages, including their 200-status not-found template."""
        return classify_job_url_validation_verdict(
            status_code,
            body_text,
            extra_bad_patterns=_MUSE_JOB_NOT_FOUND_PATTERNS,
        )

    def resolve_apply_details(
        self,
        *,
        landing_url: str | None,
        final_url: str | None,
        body_text: str | None,
    ) -> dict[str, Any]:
        """Extract the downstream application link from a Muse landing page when present."""
        apply_url = _extract_apply_on_company_site_url(body_text, final_url or landing_url)
        return {
            "apply_url": apply_url,
            "apply_host": extract_url_host(apply_url),
            "apply_portal": self.classify_apply_portal(apply_url),
        }
