"""Automated pre-scraping review tool for new providers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
import argparse
import json
import re

from bs4 import BeautifulSoup
import httpx

try:
    from app.scrapers.base.BaseProviderAdapter import ROBOTS_USER_AGENT_NAME, UAH_USER_AGENT, resolve_robots_rules
    from app.scrapers.opt_out import check_opt_out
except ModuleNotFoundError as exc:  # pragma: no cover - repo-root module execution fallback
    if exc.name != "app":
        raise
    from backend.app.scrapers.base.BaseProviderAdapter import ROBOTS_USER_AGENT_NAME, UAH_USER_AGENT, resolve_robots_rules
    from backend.app.scrapers.opt_out import check_opt_out

CHECKLIST_PATHS = ["/terms", "/tos", "/legal", "/terms-of-use"]
KEYWORDS = ["scrape", "crawl", "automated", "robot", "bot", "commercial", "reproduce", "data mining"]
ANTI_BOT_PATTERNS = {
    "akamai": ("akamai", "ak_bmsc", "akamai-origin-hop", "x-akamai"),
    "captcha": ("captcha", "g-recaptcha", "hcaptcha"),
    "cloudflare": ("cloudflare", "cf-ray", "__cf_bm", "cf-cache-status"),
    "perimeterx": ("perimeterx", "_px", "px3"),
}
EXPLICIT_TOS_PATTERNS = [
    re.compile(r"\b(no|not|may not|must not|cannot|prohibit(?:ed|s)?)\b.{0,80}\b(scrap(?:e|ing)|crawl(?:ing)?|automated|robot|bot|data mining)\b", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b(scrap(?:e|ing)|crawl(?:ing)?|automated|robot|bot|data mining)\b.{0,80}\b(forbidden|prohibited|not permitted|not allowed)\b", re.IGNORECASE | re.DOTALL),
]
JS_REQUIRED_PATTERNS = [
    "enable javascript",
    "javascript is required",
    "please turn on javascript",
    "requires javascript",
]
LOG_DIRECTORY = Path(__file__).resolve().parent / "checklist_log"


def _utc_now_iso() -> str:
    """Return the current UTC timestamp as an ISO string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_url(raw_url: str) -> str:
    """Return a normalized URL with an explicit scheme."""
    value = " ".join((raw_url or "").split())
    if not value:
        raise ValueError("A provider URL is required")
    if "://" not in value:
        value = f"https://{value}"
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Could not parse provider URL '{raw_url}'")
    return value


def _get_origin_url(url: str) -> str:
    """Return the scheme and host for one URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _response_text(response: httpx.Response) -> str:
    """Return one response body as text."""
    return response.text or ""


def _extract_text(html: str) -> str:
    """Return visible text extracted from HTML."""
    soup = BeautifulSoup(html or "", "html.parser")
    return " ".join(soup.stripped_strings)


def _build_client() -> httpx.Client:
    """Return a configured HTTP client for checklist requests."""
    return httpx.Client(
        headers={"User-Agent": UAH_USER_AGENT},
        follow_redirects=True,
        timeout=10.0,
    )


def _analyze_robots(client: httpx.Client, origin_url: str) -> dict[str, Any]:
    """Fetch and analyze robots.txt for one provider origin."""
    robots_url = urljoin(origin_url, "/robots.txt")
    try:
        response = client.get(robots_url)
    except httpx.HTTPError as exc:
        return {
            "allowed": False,
            "allowed_paths": [],
            "crawl_delay": None,
            "disallowed_paths": [],
            "error": str(exc),
            "fetched": False,
            "status_code": None,
            "uahbot_rules": None,
            "url": robots_url,
            "wildcard_rules": None,
        }

    if response.status_code != 200 or not _response_text(response).strip():
        return {
            "allowed": False,
            "allowed_paths": [],
            "crawl_delay": None,
            "disallowed_paths": [],
            "error": "robots.txt missing or unreadable",
            "fetched": False,
            "status_code": response.status_code,
            "uahbot_rules": None,
            "url": robots_url,
            "wildcard_rules": None,
        }

    resolution = resolve_robots_rules(_response_text(response), user_agent_name=ROBOTS_USER_AGENT_NAME)
    effective_rules = resolution["effective_rules"]
    return {
        "allowed": bool(resolution["allowed"]),
        "allowed_paths": list(effective_rules.get("allow_paths", [])),
        "crawl_delay": effective_rules.get("crawl_delay"),
        "disallowed_paths": list(effective_rules.get("disallow_paths", [])),
        "error": None,
        "fetched": True,
        "status_code": response.status_code,
        "uahbot_rules": resolution.get("ua_specific_rules"),
        "url": robots_url,
        "wildcard_rules": resolution.get("wildcard_rules"),
    }


def _probe_terms_page(client: httpx.Client, origin_url: str) -> dict[str, Any]:
    """Attempt to locate a provider terms or legal page."""
    attempts: list[dict[str, Any]] = []
    for candidate_path in CHECKLIST_PATHS:
        candidate_url = urljoin(origin_url, candidate_path)
        try:
            response = client.get(candidate_url)
        except httpx.HTTPError as exc:
            attempts.append({"error": str(exc), "found": False, "status_code": None, "url": candidate_url})
            continue

        content_type = (response.headers.get("content-type") or "").lower()
        html_text = _response_text(response)
        looks_html = "html" in content_type or "<html" in html_text.lower()
        found = response.status_code == 200 and looks_html and len(_extract_text(html_text)) > 20
        attempts.append({"error": None, "found": found, "status_code": response.status_code, "url": str(response.url)})
        if found:
            return {
                "attempts": attempts,
                "found": True,
                "html": html_text,
                "status_code": response.status_code,
                "url": str(response.url),
            }

    return {
        "attempts": attempts,
        "found": False,
        "html": "",
        "status_code": None,
        "url": None,
    }


def _keyword_contexts(text: str, keyword: str, *, radius: int = 100) -> list[str]:
    """Return short surrounding excerpts for keyword matches."""
    contexts: list[str] = []
    pattern = re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
    for match in pattern.finditer(text):
        start = max(match.start() - radius, 0)
        end = min(match.end() + radius, len(text))
        contexts.append(" ".join(text[start:end].split()))
        if len(contexts) >= 3:
            break
    return contexts


def _scan_terms_text(html: str) -> dict[str, Any]:
    """Scan a terms page for automation-related language and keyword context."""
    text = _extract_text(html)
    matches: list[dict[str, Any]] = []
    for keyword in KEYWORDS:
        contexts = _keyword_contexts(text, keyword)
        if contexts:
            matches.append({"contexts": contexts, "keyword": keyword})

    explicit = any(pattern.search(text) for pattern in EXPLICIT_TOS_PATTERNS)
    ambiguous = bool(matches) and not explicit
    return {
        "ambiguous_language": ambiguous,
        "explicit_anti_automation": explicit,
        "matches": matches,
        "text_length": len(text),
    }


def _analyze_js_render(client: httpx.Client, url: str) -> dict[str, Any]:
    """Check whether the provider landing page appears usable without JavaScript."""
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        return {
            "js_required": True,
            "renders_without_js": False,
            "signals": [str(exc)],
            "status_code": None,
            "url": url,
        }

    html = _response_text(response)
    soup = BeautifulSoup(html, "html.parser")
    visible_text = " ".join(soup.stripped_strings)
    script_count = len(soup.find_all("script"))
    lower_html = html.lower()
    signals: list[str] = []
    if len(visible_text) < 120 and script_count >= 3:
        signals.append("Low visible text with multiple script tags")
    for indicator in JS_REQUIRED_PATTERNS:
        if indicator in lower_html:
            signals.append(indicator)
    js_required = bool(signals)
    return {
        "js_required": js_required,
        "renders_without_js": not js_required and response.status_code == 200,
        "signals": signals,
        "status_code": response.status_code,
        "url": str(response.url),
    }


def _analyze_anti_bot(page_response: httpx.Response) -> dict[str, Any]:
    """Inspect one response for common anti-bot infrastructure signals."""
    body_text = _response_text(page_response).lower()
    header_items = {key.lower(): value.lower() for key, value in page_response.headers.items()}
    cookie_names = {str(key).lower() for key in getattr(page_response, "cookies", {}).keys()}

    signals: list[str] = []
    for vendor, indicators in ANTI_BOT_PATTERNS.items():
        if any(indicator in body_text for indicator in indicators):
            signals.append(vendor)
            continue
        if any(indicator in header_items for indicator in indicators):
            signals.append(vendor)
            continue
        if any(indicator in value for value in header_items.values() for indicator in indicators):
            signals.append(vendor)
            continue
        if any(indicator in cookie_names for indicator in indicators):
            signals.append(vendor)
            continue

    deduped_signals = sorted(set(signals))
    return {
        "detected": bool(deduped_signals),
        "headers": dict(page_response.headers),
        "signals": deduped_signals,
    }


def _determine_verdict(report: dict[str, Any]) -> str:
    """Return the checklist verdict from collected signals."""
    if report["opt_out"]["is_opted_out"]:
        return "REJECTED"
    if not report["robots_txt"]["allowed"]:
        return "REJECTED"
    if report["terms_of_service"]["scan"].get("explicit_anti_automation"):
        return "REJECTED"
    if not report["terms_of_service"]["found"]:
        return "NEEDS REVIEW"
    if report["terms_of_service"]["scan"].get("ambiguous_language"):
        return "NEEDS REVIEW"
    if report["anti_bot"]["detected"]:
        return "NEEDS REVIEW"
    if report["render_check"]["js_required"]:
        return "NEEDS REVIEW"
    return "APPROVED"


def _write_log(report: dict[str, Any]) -> str:
    """Write the checklist report to a dated JSON log file."""
    LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
    domain = (urlparse(report["provider_url"]).netloc or "provider").replace(":", "-")
    date_label = datetime.now(timezone.utc).date().isoformat()
    log_path = LOG_DIRECTORY / f"{domain}-{date_label}.json"
    with log_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return str(log_path)


def run_checklist(url: str) -> dict[str, Any]:
    """Run the automated pre-scraping checklist for one provider URL."""
    normalized_url = _normalize_url(url)
    origin_url = _get_origin_url(normalized_url)

    with _build_client() as client:
        robots = _analyze_robots(client, origin_url)
        terms_page = _probe_terms_page(client, origin_url)
        if terms_page["found"]:
            terms_scan = _scan_terms_text(terms_page.get("html", ""))
        else:
            terms_scan = {
                "ambiguous_language": False,
                "explicit_anti_automation": False,
                "matches": [],
                "text_length": 0,
            }
        try:
            landing_response = client.get(normalized_url)
        except httpx.HTTPError as exc:
            landing_response = httpx.Response(
                status_code=0,
                request=httpx.Request("GET", normalized_url),
                text=str(exc),
            )
        render_check = _analyze_js_render(client, normalized_url)
        anti_bot = _analyze_anti_bot(landing_response)

    report = {
        "anti_bot": anti_bot,
        "checked_at_utc": _utc_now_iso(),
        "opt_out": {
            "is_opted_out": check_opt_out(origin_url),
        },
        "provider_origin": origin_url,
        "provider_url": normalized_url,
        "render_check": render_check,
        "robots_txt": robots,
        "terms_of_service": {
            "attempts": terms_page["attempts"],
            "found": terms_page["found"],
            "scan": terms_scan,
            "status_code": terms_page["status_code"],
            "url": terms_page["url"],
        },
    }
    report["verdict"] = _determine_verdict(report)
    report["log_file"] = _write_log(report)
    return report


def format_summary(report: dict[str, Any]) -> str:
    """Return a human-readable CLI summary for one checklist run."""
    anti_bot_signals = ", ".join(report["anti_bot"]["signals"]) if report["anti_bot"]["signals"] else "none"
    tos_url = report["terms_of_service"]["url"] or "not found"
    crawl_delay = report["robots_txt"]["crawl_delay"]
    crawl_delay_label = "none" if crawl_delay is None else str(crawl_delay)
    return "\n".join(
        [
            "UAH Pre-Scraping Checklist",
            f"Provider URL: {report['provider_url']}",
            f"Robots allowed: {'yes' if report['robots_txt']['allowed'] else 'no'}",
            f"Crawl-delay: {crawl_delay_label}",
            f"ToS page: {tos_url}",
            f"ToS explicit anti-automation language: {'yes' if report['terms_of_service']['scan']['explicit_anti_automation'] else 'no'}",
            f"JS required: {'yes' if report['render_check']['js_required'] else 'no'}",
            f"Anti-bot signals: {anti_bot_signals}",
            f"Opted out: {'yes' if report['opt_out']['is_opted_out'] else 'no'}",
            f"Verdict: {report['verdict']}",
            f"Log file: {report['log_file']}",
        ]
    )


def main() -> None:
    """Run the checklist CLI."""
    parser = argparse.ArgumentParser(description="Run UAH's pre-scraping checklist for a provider URL.")
    parser.add_argument("--url", required=True, help="Provider homepage or job board URL.")
    args = parser.parse_args()
    report = run_checklist(args.url)
    print(format_summary(report))


if __name__ == "__main__":
    main()
