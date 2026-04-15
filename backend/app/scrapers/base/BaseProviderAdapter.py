"""Base contract and shared helpers for ethical scraper adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urljoin, urlparse
import time

import httpx

try:
    from app.schemas.job import NormalizedJob
    from app.scrapers.opt_out import check_opt_out
except ModuleNotFoundError as exc:  # pragma: no cover - repo-root module execution fallback
    if exc.name != "app":
        raise
    from backend.app.schemas.job import NormalizedJob
    from backend.app.scrapers.opt_out import check_opt_out

UAH_USER_AGENT = "UAHBot/1.0; +https://uahapp.com/scraping-policy"
ROBOTS_USER_AGENT_NAME = "UAHBot"


class ProviderOptedOutError(RuntimeError):
    """Raised when a provider has requested permanent removal from indexing."""


def _strip_inline_comment(line: str) -> str:
    """Return a robots.txt line without trailing inline comments."""
    return line.split("#", 1)[0].strip()


def _normalize_rule_path(value: str) -> str:
    """Return one normalized robots path rule."""
    cleaned = (value or "").strip()
    if not cleaned:
        return ""
    if cleaned.startswith("/"):
        return cleaned
    return f"/{cleaned}"


def _dedupe_paths(values: list[str]) -> list[str]:
    """Return stable unique path values."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = _normalize_rule_path(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _match_rule_length(path: str, rules: list[str]) -> int:
    """Return the longest matching robots rule length for a path."""
    matches = [len(rule) for rule in rules if rule and path.startswith(rule)]
    return max(matches, default=0)


def is_path_allowed(path: str, allow_paths: list[str], disallow_paths: list[str]) -> bool:
    """Evaluate one path against allow/disallow robots rules."""
    normalized_path = urlparse(path).path or "/"
    longest_allow = _match_rule_length(normalized_path, allow_paths)
    longest_disallow = _match_rule_length(normalized_path, disallow_paths)
    if longest_disallow == 0:
        return True
    return longest_allow >= longest_disallow


def parse_robots_txt(text: str) -> list[dict[str, Any]]:
    """Parse robots.txt text into grouped user-agent rule blocks."""
    groups: list[dict[str, Any]] = []
    current_group: dict[str, Any] | None = None
    seen_rule = False

    for raw_line in (text or "").splitlines():
        line = _strip_inline_comment(raw_line)
        if not line or ":" not in line:
            continue

        field_name, raw_value = line.split(":", 1)
        directive = field_name.strip().lower()
        value = raw_value.strip()

        if directive == "user-agent":
            if current_group is None or seen_rule:
                if current_group is not None:
                    groups.append(current_group)
                current_group = {
                    "user_agents": [],
                    "allow_paths": [],
                    "disallow_paths": [],
                    "crawl_delay": None,
                }
                seen_rule = False
            current_group["user_agents"].append(value)
            continue

        if current_group is None:
            continue

        seen_rule = True
        if directive == "allow":
            normalized = _normalize_rule_path(value)
            if normalized:
                current_group["allow_paths"].append(normalized)
        elif directive == "disallow":
            normalized = _normalize_rule_path(value)
            if normalized:
                current_group["disallow_paths"].append(normalized)
        elif directive == "crawl-delay":
            try:
                current_group["crawl_delay"] = max(float(value), 0.0)
            except ValueError:
                continue

    if current_group is not None:
        groups.append(current_group)

    return groups


def _combine_rule_groups(groups: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Merge matching robots groups into one effective ruleset."""
    if not groups:
        return None
    crawl_delays = [group["crawl_delay"] for group in groups if group.get("crawl_delay") is not None]
    return {
        "user_agents": [agent for group in groups for agent in group.get("user_agents", [])],
        "allow_paths": _dedupe_paths([path for group in groups for path in group.get("allow_paths", [])]),
        "disallow_paths": _dedupe_paths([path for group in groups for path in group.get("disallow_paths", [])]),
        "crawl_delay": max(crawl_delays) if crawl_delays else None,
    }


def resolve_robots_rules(text: str, *, user_agent_name: str = ROBOTS_USER_AGENT_NAME) -> dict[str, Any]:
    """Resolve robots rules with exact user-agent precedence over wildcard rules."""
    groups = parse_robots_txt(text)
    normalized_user_agent = (user_agent_name or "").strip().lower()

    specific_groups = [
        group for group in groups if normalized_user_agent in {agent.strip().lower() for agent in group.get("user_agents", [])}
    ]
    wildcard_groups = [
        group for group in groups if "*" in {agent.strip().lower() for agent in group.get("user_agents", [])}
    ]

    specific_rules = _combine_rule_groups(specific_groups)
    wildcard_rules = _combine_rule_groups(wildcard_groups)
    effective_rules = specific_rules or wildcard_rules or {
        "user_agents": [],
        "allow_paths": [],
        "disallow_paths": [],
        "crawl_delay": None,
    }

    return {
        "ua_specific_rules": specific_rules,
        "wildcard_rules": wildcard_rules,
        "effective_rules": effective_rules,
        "allowed": is_path_allowed("/", effective_rules["allow_paths"], effective_rules["disallow_paths"]),
    }


class BaseProviderAdapter(ABC):
    """Abstract ethical scraper adapter that normalizes provider listings for UAH."""

    def __init__(self) -> None:
        """Initialize per-adapter request state and robots caches."""
        self._last_request_at: float | None = None
        self._robots_cache: dict[str, Any] | None = None
        self._robots_resolution_cache: dict[str, Any] | None = None

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the human-readable provider name."""

    @abstractmethod
    def get_base_url(self) -> str:
        """Return the provider base domain used for robots and opt-out checks."""

    def get_user_agent(self) -> str:
        """Return UAH's descriptive scraping user agent."""
        return UAH_USER_AGENT

    def get_rate_limit_seconds(self) -> float:
        """Return the adapter's minimum pacing between requests."""
        return 2.0

    @abstractmethod
    def fetch_listings(self, query: str | None, location: str | None, page: int) -> list[dict[str, Any]]:
        """Fetch raw provider listings for one query, location, and page."""

    @abstractmethod
    def normalize_listing(self, raw: dict[str, Any]) -> NormalizedJob:
        """Normalize one raw provider listing into UAH's standard schema."""

    def fetch_and_normalize(self, query: str | None, location: str | None, page: int) -> list[NormalizedJob]:
        """Fetch raw listings and normalize them into UAH's schema."""
        return [self.normalize_listing(raw) for raw in self.fetch_listings(query=query, location=location, page=page)]

    def check_robots_txt(self) -> dict[str, Any]:
        """Fetch and parse robots.txt for the provider domain."""
        if self._robots_cache is not None:
            return dict(self._robots_cache)

        robots_url = urljoin(self._get_origin_url(), "/robots.txt")
        result = {
            "allowed": False,
            "crawl_delay": None,
            "disallowed_paths": [],
        }

        try:
            with httpx.Client(
                headers={"User-Agent": self.get_user_agent()},
                follow_redirects=True,
                timeout=10.0,
            ) as client:
                response = client.get(robots_url)
        except httpx.HTTPError:
            self._robots_cache = result
            self._robots_resolution_cache = None
            return dict(result)

        if response.status_code != 200 or not (response.text or "").strip():
            self._robots_cache = result
            self._robots_resolution_cache = None
            return dict(result)

        resolution = resolve_robots_rules(response.text, user_agent_name=ROBOTS_USER_AGENT_NAME)
        effective_rules = resolution["effective_rules"]
        result = {
            "allowed": bool(resolution["allowed"]),
            "crawl_delay": effective_rules.get("crawl_delay"),
            "disallowed_paths": list(effective_rules.get("disallow_paths", [])),
        }
        self._robots_cache = result
        self._robots_resolution_cache = resolution
        return dict(result)

    def get_opt_out_status(self) -> bool:
        """Return whether the provider is present in UAH's opt-out registry."""
        return check_opt_out(self.get_base_url())

    def is_active(self) -> bool:
        """Return whether the provider is eligible for future activation."""
        if self.get_opt_out_status():
            return False
        try:
            robots = self.check_robots_txt()
        except Exception:
            return False
        return bool(robots.get("allowed", False))

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout_seconds: float = 10.0,
    ) -> httpx.Response:
        """Perform one paced HTTP request using the UAHBot user agent."""
        if self.get_opt_out_status():
            raise ProviderOptedOutError(
                f"{self.get_provider_name()} has requested removal from UAH indexing."
            )

        robots = self.check_robots_txt()
        if not self._path_allowed(url, robots_info=robots):
            raise PermissionError(
                f"{self.get_provider_name()} robots.txt does not allow requests to {urlparse(url).path or '/'}."
            )

        self._sleep_if_needed(self._resolve_request_delay_seconds(robots.get("crawl_delay")))
        request_headers = {"User-Agent": self.get_user_agent()}
        if headers:
            request_headers.update(headers)

        try:
            with httpx.Client(
                headers=request_headers,
                follow_redirects=True,
                timeout=max(float(timeout_seconds), 1.0),
            ) as client:
                return client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_body,
                )
        finally:
            self._last_request_at = time.monotonic()

    def _get_origin_url(self) -> str:
        """Return the scheme and host for the provider base URL."""
        parsed = urlparse(self.get_base_url())
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
        return (self.get_base_url() or "").rstrip("/")

    def _path_allowed(self, url: str, *, robots_info: dict[str, Any] | None = None) -> bool:
        """Return whether one request path is allowed by cached robots rules."""
        if self._robots_resolution_cache is None:
            robots = robots_info or self.check_robots_txt()
            return bool(robots.get("allowed", False))

        effective_rules = self._robots_resolution_cache.get("effective_rules", {})
        return is_path_allowed(
            urlparse(url).path or "/",
            effective_rules.get("allow_paths", []),
            effective_rules.get("disallow_paths", []),
        )

    def _resolve_request_delay_seconds(self, crawl_delay: float | None) -> float:
        """Return the greater of adapter delay, robots crawl-delay, and UAH's floor."""
        requested_delay = max(float(self.get_rate_limit_seconds() or 0.0), 1.0)
        robots_delay = max(float(crawl_delay or 0.0), 0.0)
        return max(requested_delay, robots_delay, 1.0)

    def _sleep_if_needed(self, minimum_delay_seconds: float) -> None:
        """Sleep long enough to satisfy the current pacing window."""
        if self._last_request_at is None:
            return
        elapsed = time.monotonic() - self._last_request_at
        remaining = max(float(minimum_delay_seconds) - elapsed, 0.0)
        if remaining > 0:
            time.sleep(remaining)


__all__ = [
    "BaseProviderAdapter",
    "ProviderOptedOutError",
    "ROBOTS_USER_AGENT_NAME",
    "UAH_USER_AGENT",
    "is_path_allowed",
    "parse_robots_txt",
    "resolve_robots_rules",
]
