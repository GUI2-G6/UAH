from __future__ import annotations

from datetime import datetime, timezone
import html
import re

_TAG_RE = re.compile(r"<[^>]+>")
_REMOTE_RE = re.compile(r"\b(remote|work from home|telecommute|distributed|anywhere)\b", re.IGNORECASE)
_HYBRID_RE = re.compile(r"\bhybrid\b", re.IGNORECASE)

_CATEGORY_KEYWORDS = (
    ("Software Engineering", ("engineer", "engineering", "developer", "software", "backend", "frontend", "full stack", "devops", "sre", "platform", "cloud", "security", "qa", "test automation")),
    ("Data and Analytics", ("data", "analytics", "machine learning", "ml", "ai", "scientist", "analyst", "business intelligence")),
    ("Design and UX", ("design", "designer", "ux", "ui", "product design", "visual design")),
    ("Product Management", ("product manager", "product management", "product owner", "program manager", "project manager")),
    ("Accounting and Finance", ("finance", "financial", "accounting", "accountant", "controller", "fp&a", "payroll")),
    ("Human Resources and Recruitment", ("recruit", "recruiter", "talent", "human resources", "people ops", "people operations", "hr")),
    ("Business Operations", ("operations", "business operations", "strategy", "chief of staff", "office manager", "program operations")),
    ("Sales", ("sales", "account executive", "business development", "partnerships")),
    ("Marketing", ("marketing", "growth", "seo", "brand", "content", "demand generation", "communications")),
    ("Customer Service", ("support", "customer service", "customer success", "technical support", "help desk")),
)


def clean_html_text(value: str | None) -> str:
    """Return a plain-text version of one provider HTML fragment."""
    plain = _TAG_RE.sub(" ", value or "")
    plain = html.unescape(plain)
    return " ".join(plain.split())


def dedupe_strings(values: list[str]) -> list[str]:
    """Return a stable list of unique non-empty strings."""
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


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse a provider ISO timestamp into UTC when possible."""
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


def parse_unix_timestamp(value: int | float | str | None) -> datetime | None:
    """Parse a unix timestamp value into UTC."""
    if value in {None, ""}:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    try:
        return datetime.fromtimestamp(numeric, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def parse_iso_datetime_with_trimmed_fraction(value: str | None) -> datetime | None:
    """Parse an ISO timestamp while trimming unsupported 7-digit fractions."""
    raw = (value or "").strip()
    if not raw:
        return None
    if "." in raw:
        head, tail = raw.split(".", 1)
        fraction = tail
        suffix = ""
        if "+" in tail:
            fraction, suffix = tail.split("+", 1)
            suffix = f"+{suffix}"
        elif "Z" in tail:
            fraction = tail.replace("Z", "")
            suffix = "Z"
        if len(fraction) > 6:
            raw = f"{head}.{fraction[:6]}{suffix}"
    return parse_iso_datetime(raw)


def infer_remote_flag(*, title: str | None = None, location: str | None = None, description: str | None = None) -> bool:
    """Infer whether a listing is remote from common text hints."""
    haystack = " ".join([title or "", location or "", description or ""])
    return bool(_REMOTE_RE.search(haystack))


def infer_hybrid_flag(*, title: str | None = None, location: str | None = None, description: str | None = None) -> bool:
    """Infer whether a listing mentions hybrid work."""
    haystack = " ".join([title or "", location or "", description or ""])
    return bool(_HYBRID_RE.search(haystack))


def normalize_provider_categories(*, values: list[str] | None = None, title: str | None = None, description: str | None = None) -> list[str]:
    """Map provider-native tags into the broad category vocabulary used by UAH."""
    searchable = " ".join([title or "", description or "", " ".join(values or [])]).lower()
    matched: list[str] = []
    for category_name, keywords in _CATEGORY_KEYWORDS:
        if any(keyword in searchable for keyword in keywords):
            matched.append(category_name)
    return dedupe_strings(matched)


def normalize_job_type(values: list[str] | None, *, fallback: str | None = None) -> str | None:
    """Normalize provider-native employment type labels."""
    type_map = {
        "full time": "full_time",
        "full-time": "full_time",
        "part time": "part_time",
        "part-time": "part_time",
        "contract": "contract",
        "internship": "internship",
        "temporary": "temporary",
        "volunteer": "volunteer",
        "freelance": "contract",
    }
    candidates = list(values or [])
    if fallback:
        candidates.append(fallback)
    for value in candidates:
        normalized = " ".join((value or "").strip().lower().split())
        mapped = type_map.get(normalized)
        if mapped:
            return mapped
    return None


def normalize_experience_level(*, values: list[str] | None = None, title: str | None = None) -> str | None:
    """Infer UAH experience level from provider-native labels and title text."""
    mapping = {
        "internship": "internship",
        "entry": "entry",
        "entry level": "entry",
        "junior": "entry",
        "jr": "entry",
        "berufseinstieg": "entry",
        "mid": "mid",
        "senior": "senior",
        "sr": "senior",
        "lead": "manager",
        "teamleitung": "manager",
        "management": "manager",
        "manager": "manager",
        "director": "director",
        "vp": "vp",
        "principal": "director",
        "staff": "director",
    }
    candidates = list(values or [])
    if title:
        candidates.append(title)
    for value in candidates:
        normalized = " ".join((value or "").strip().lower().split())
        for key, mapped in mapping.items():
            if re.search(rf"\b{re.escape(key)}\b", normalized):
                return mapped
    return None
