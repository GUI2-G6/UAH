"""
API Routes
==========

All /api/* endpoints live here.

How routing works:
  - This file defines an APIRouter that gets mounted in main.py.
  - Each endpoint is a decorated async function.
  - FastAPI automatically generates OpenAPI/Swagger docs from the
    type hints and docstrings you provide.

Where to add new routes:
  - Simple CRUD routes can be added directly here.
  - As the app grows, split into sub-routers:
      app/api/v1/users.py
      app/api/v1/jobs.py
    and include them in main.py with version prefixes.

Where business logic should go:
  - Keep route handlers thin — they should validate input, call a
    service function, and return the result.
  - Business logic belongs in a services/ directory:
      app/services/scraper.py    — web scraping with BeautifulSoup
      app/services/jobs.py       — job application logic
  - Import and call those services from route handlers.

Where scraping services will live:
  - app/services/scraper.py (create when needed)
  - Use BeautifulSoup + httpx/requests for scraping.
  - Keep scraping logic fully decoupled from route handlers.

How DB session will be injected later:
  - Import `get_db` from app.db.session
  - Add it as a FastAPI dependency:
      from fastapi import Depends
      from app.db.session import get_db
      from sqlalchemy.orm import Session

      @router.get("/items")
      async def list_items(db: Session = Depends(get_db)):
          return db.query(Item).all()
"""
import asyncio
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import logging
import os
import secrets
import httpx
import re
import time
from urllib.parse import urlencode, urlparse
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, require_admin_user
from app.models.user import User, SavedJob
from app.db.session import get_db
from app.google.service import GoogleAuthService
from app.schemas.user import SaveJobRequest
from app.core.auth_session import (
    access_token_expire_seconds_for_client,
    create_access_token_for_client,
    resolve_auth_client,
)
from app.core.auth_cookie import set_auth_cookie
from typing import Optional, List, Any
from app.services.geolocation import (
    geocode_query,
    km_to_miles,
    list_country_cities,
    miles_to_km,
    find_cities_in_radius,
    resolve_ip_location,
    reverse_geocode,
)
from app.services.location_country_reference import REAL_COUNTRY_CODES, country_name_from_code
from app.services.muse_location_index import (
    ensure_muse_location_index,
    list_supported_countries,
    list_supported_locations_for_country,
    refresh_muse_location_index,
)
from app.services.resume_parser import get_pipeline_availability
from app.core.config import settings
from app.models.muse_location import MuseSupportedLocation


router = APIRouter()
logger = logging.getLogger(__name__)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
MUSE_API_KEY = os.getenv("MUSE_API_KEY")

REMOTE_TEXT_PATTERN = re.compile(
    r"\b(remote|work\s*from\s*home|telecommute|telecommuting|distributed|anywhere)\b",
    flags=re.IGNORECASE,
)
HYBRID_TEXT_PATTERN = re.compile(r"\bhybrid\b", flags=re.IGNORECASE)
TIMEZONE_TOKEN_PATTERN = re.compile(
    r"\b(eastern|central|mountain|pacific|est|edt|cst|cdt|mst|mdt|pst|pdt)\b",
    flags=re.IGNORECASE,
)
EXCLUSION_SEGMENT_PATTERN = re.compile(r"(?:except|excluding)\s+([^.;\n]+)", flags=re.IGNORECASE)
EXCLUSION_INLINE_PATTERN = re.compile(
    r"(?:not\s+available\s+in|unavailable\s+in|outside\s+of)\s+([^.;\n]+)",
    flags=re.IGNORECASE,
)

UNIFIED_CATEGORY_GROUPS = {
    "tech": [
        "Software Engineer",
        "Software Engineering",
        "Computer and IT",
        "IT",
        "Data and Analytics",
        "Data Science",
        "Design and UX",
        "UX",
        "Science and Engineering",
    ],
    "finance": [
        "Accounting",
        "Accounting and Finance",
        "Finance",
        "Real Estate",
    ],
    "product": [
        "Product",
        "Product Management",
        "Project Management",
    ],
    "people": [
        "HR",
        "Human Resources and Recruitment",
        "Recruiting",
        "Social Services",
    ],
    "business and operations": [
        "Business Operations",
        "Corporate",
        "Operations",
        "Office Administration",
        "Administration and Office",
    ],
    "sales and marketing": [
        "Sales",
        "Marketing",
        "Advertising and Marketing",
        "Public Relations",
        "Media, PR, and Communications",
        "Account Management",
        "Account Management/Customer Success",
    ],
    "customer and support": [
        "Customer Service",
        "Education",
        "Legal Services",
    ],
}

CATEGORY_GROUP_ALIAS = {
    "technology": "tech",
    "engineering": "tech",
    "tech": "tech",
    "fintech": "finance",
    "finance": "finance",
    "product": "product",
    "people": "people",
    "hr": "people",
    "operations": "business and operations",
    "business": "business and operations",
    "sales": "sales and marketing",
    "marketing": "sales and marketing",
    "support": "customer and support",
}

CATEGORY_GROUP_DISPLAY_NAMES = {
    "tech": "Tech",
    "finance": "Finance",
    "product": "Product",
    "people": "People",
    "business and operations": "Business and Operations",
    "sales and marketing": "Sales and Marketing",
    "customer and support": "Customer and Support",
}

MUSE_LEVEL_OPTIONS = [
    "Internship",
    "Entry Level",
    "Mid Level",
    "Senior Level",
    "Management",
]

LEVEL_VALUE_ALIASES = {
    "internship": "internship",
    "entry": "entry",
    "entry level": "entry",
    "mid": "mid",
    "mid level": "mid",
    "senior": "senior",
    "senior level": "senior",
    "manager": "manager",
    "management": "manager",
    "director": "director",
    "vp": "vp",
}

LEVEL_VALUE_LABELS = {
    "internship": "Internship",
    "entry": "Entry",
    "mid": "Mid",
    "senior": "Senior",
    "manager": "Manager",
    "director": "Director",
    "vp": "VP",
}

_JOBS_CACHE: dict[str, dict[str, Any]] = {}
_JOB_URL_VALIDATION_CACHE: dict[str, dict[str, Any]] = {}

INVALID_JOB_URL_STATUSES = {404, 410, 500, 502, 503, 504}

TIMEZONE_FAMILY_ALIASES = {
    "eastern": "ET",
    "est": "ET",
    "edt": "ET",
    "central": "CT",
    "cst": "CT",
    "cdt": "CT",
    "mountain": "MT",
    "mst": "MT",
    "mdt": "MT",
    "pacific": "PT",
    "pst": "PT",
    "pdt": "PT",
}

US_STATE_TO_TIMEZONE_FAMILY = {
    "AL": "CT", "AK": "PT", "AZ": "MT", "AR": "CT", "CA": "PT", "CO": "MT", "CT": "ET", "DC": "ET",
    "DE": "ET", "FL": "ET", "GA": "ET", "HI": "PT", "IA": "CT", "ID": "MT", "IL": "CT", "IN": "ET",
    "KS": "CT", "KY": "ET", "LA": "CT", "MA": "ET", "MD": "ET", "ME": "ET", "MI": "ET", "MN": "CT",
    "MO": "CT", "MS": "CT", "MT": "MT", "NC": "ET", "ND": "CT", "NE": "CT", "NH": "ET", "NJ": "ET",
    "NM": "MT", "NV": "PT", "NY": "ET", "OH": "ET", "OK": "CT", "OR": "PT", "PA": "ET", "RI": "ET",
    "SC": "ET", "SD": "CT", "TN": "CT", "TX": "CT", "UT": "MT", "VA": "ET", "VT": "ET", "WA": "PT",
    "WI": "CT", "WV": "ET", "WY": "MT",
}

METRO_ALIAS_STATES = {
    "bay area": {"CA"},
    "san francisco bay": {"CA"},
    "san francisco bay metro area": {"CA"},
    "nyc": {"NY", "NJ", "CT"},
    "nyc metro area": {"NY", "NJ", "CT"},
    "new york city metro area": {"NY", "NJ", "CT"},
    "washington dc metro area": {"DC", "VA", "MD"},
    "washington d c metro area": {"DC", "VA", "MD"},
}

CONSTRAINT_CONFIDENCE_RANK = {
    "low": 0,
    "medium": 1,
    "high": 2,
}


def _normalize_text(value: Optional[str]) -> str:
    return " ".join((value or "").strip().lower().split())


def _normalize_constraint_text(value: Optional[str]) -> str:
    return _normalize_text((value or "").replace("/", " ").replace("-", " "))


def _build_category_groups_payload() -> List[dict[str, Any]]:
    payload: List[dict[str, Any]] = []
    for key, categories in UNIFIED_CATEGORY_GROUPS.items():
        payload.append(
            {
                "key": key,
                "name": CATEGORY_GROUP_DISPLAY_NAMES.get(key, key.title()),
                "muse_categories": list(categories),
            }
        )
    return payload


def _build_category_aliases_payload() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for alias, group_key in CATEGORY_GROUP_ALIAS.items():
        display_name = CATEGORY_GROUP_DISPLAY_NAMES.get(group_key)
        if display_name:
            aliases[alias] = display_name
    return aliases


def _normalize_level_metadata_value(raw_value: Optional[str]) -> Optional[str]:
    normalized = _normalize_text(raw_value)
    if not normalized:
        return None
    return LEVEL_VALUE_ALIASES.get(normalized, normalized)


def _label_level_metadata_value(value: str) -> str:
    normalized = _normalize_text(value)
    if normalized in LEVEL_VALUE_LABELS:
        return LEVEL_VALUE_LABELS[normalized]
    return " ".join(part.capitalize() for part in normalized.split())


def _build_default_category_values_payload() -> List[dict[str, Any]]:
    seen: set[str] = set()
    values: List[str] = []
    for categories in UNIFIED_CATEGORY_GROUPS.values():
        for raw_value in categories:
            value = " ".join(str(raw_value or "").split())
            if not value:
                continue
            key = value.lower()
            if key in seen:
                continue
            seen.add(key)
            values.append(value)

    return [
        {"value": value, "observed_count": 0}
        for value in sorted(values, key=lambda item: item.lower())
    ]


def _build_default_level_values_payload() -> List[dict[str, Any]]:
    return [
        {"value": value, "label": label, "observed_count": 0}
        for value, label in LEVEL_VALUE_LABELS.items()
    ]


def _build_job_filter_metadata_query(db: Session):
    from app.models.job import Job
    from app.providers.registry import list_enabled_provider_names

    display_enabled_providers = list_enabled_provider_names(control_name="display")
    query = db.query(Job).filter(Job.is_active.is_(True)).filter(
        or_(Job.provider_url_status.is_(None), Job.provider_url_status != "bad")
    )

    if not display_enabled_providers:
        return query.filter(False)
    return query.filter(Job.provider.in_(display_enabled_providers))


def _query_observed_category_counts(db: Session) -> List[tuple[str, int]]:
    from app.models.job import Job

    base_query = _build_job_filter_metadata_query(db)
    category_rows = base_query.with_entities(func.unnest(Job.categories).label("value")).subquery()
    rows = (
        db.query(
            func.btrim(category_rows.c.value).label("value"),
            func.count().label("observed_count"),
        )
        .filter(category_rows.c.value.is_not(None))
        .filter(func.length(func.btrim(category_rows.c.value)) > 0)
        .group_by(func.btrim(category_rows.c.value))
        .all()
    )
    return [
        (" ".join(str(row.value or "").split()), int(row.observed_count or 0))
        for row in rows
        if " ".join(str(row.value or "").split())
    ]


def _query_observed_level_counts(db: Session) -> List[tuple[str, int]]:
    from app.models.job import Job

    rows = (
        _build_job_filter_metadata_query(db)
        .with_entities(
            Job.experience_level.label("value"),
            func.count(Job.id).label("observed_count"),
        )
        .filter(Job.experience_level.is_not(None))
        .group_by(Job.experience_level)
        .all()
    )
    return [
        (" ".join(str(row.value or "").split()), int(row.observed_count or 0))
        for row in rows
        if " ".join(str(row.value or "").split())
    ]


def _query_observed_country_counts(db: Session) -> List[tuple[str, str, int]]:
    from app.models.job import Job

    rows = (
        _build_job_filter_metadata_query(db)
        .with_entities(
            Job.location_country_code.label("code"),
            Job.location_country_name.label("name"),
            func.count(Job.id).label("observed_count"),
        )
        .filter(Job.location_country_code.is_not(None))
        .filter(func.length(func.btrim(Job.location_country_code)) > 0)
        .group_by(Job.location_country_code, Job.location_country_name)
        .all()
    )
    return [
        (
            " ".join(str(row.code or "").split()).upper(),
            " ".join(str(row.name or "").split()),
            int(row.observed_count or 0),
        )
        for row in rows
        if " ".join(str(row.code or "").split())
    ]


def _query_observed_provider_counts(db: Session) -> List[tuple[str, int]]:
    from app.models.job import Job

    rows = (
        _build_job_filter_metadata_query(db)
        .with_entities(
            Job.provider.label("value"),
            func.count(Job.id).label("observed_count"),
        )
        .filter(Job.provider.is_not(None))
        .group_by(Job.provider)
        .all()
    )
    return [
        (" ".join(str(row.value or "").split()).lower(), int(row.observed_count or 0))
        for row in rows
        if " ".join(str(row.value or "").split())
    ]


def _query_observed_company_counts(db: Session) -> List[tuple[str, int]]:
    from app.models.job import Job

    rows = (
        _build_job_filter_metadata_query(db)
        .with_entities(
            Job.company.label("value"),
            func.count(Job.id).label("observed_count"),
        )
        .filter(Job.company.is_not(None))
        .filter(func.length(func.btrim(Job.company)) > 0)
        .group_by(Job.company)
        .all()
    )
    return [
        (" ".join(str(row.value or "").split()), int(row.observed_count or 0))
        for row in rows
        if " ".join(str(row.value or "").split())
    ]


def _build_observed_category_values_payload(db: Optional[Session] = None) -> List[dict[str, Any]]:
    counts: dict[str, int] = {}

    if db is not None:
        try:
            for value, observed_count in _query_observed_category_counts(db):
                counts[value] = counts.get(value, 0) + max(int(observed_count or 0), 0)
        except Exception:
            counts = {}

    if not counts:
        return _build_default_category_values_payload()

    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower(), item[0]))
    return [
        {"value": value, "observed_count": observed_count}
        for value, observed_count in ordered
    ]


def _build_observed_level_values_payload(db: Optional[Session] = None) -> List[dict[str, Any]]:
    counts: dict[str, int] = {}

    if db is not None:
        try:
            for raw_value, observed_count in _query_observed_level_counts(db):
                canonical_value = _normalize_level_metadata_value(raw_value)
                if not canonical_value:
                    continue
                counts[canonical_value] = counts.get(canonical_value, 0) + max(int(observed_count or 0), 0)
        except Exception:
            counts = {}

    if not counts:
        return _build_default_level_values_payload()

    ordered = sorted(
        counts.items(),
        key=lambda item: (-item[1], _label_level_metadata_value(item[0]).lower(), item[0]),
    )
    return [
        {
            "value": value,
            "label": _label_level_metadata_value(value),
            "observed_count": observed_count,
        }
        for value, observed_count in ordered
    ]


def _build_observed_country_values_payload(db: Optional[Session] = None) -> List[dict[str, Any]]:
    if db is None:
        return []

    counts: dict[str, dict[str, Any]] = {}
    try:
        for code, name, observed_count in _query_observed_country_counts(db):
            if not code:
                continue
            if code not in REAL_COUNTRY_CODES:
                continue
            current = counts.setdefault(
                code,
                {
                    "code": code,
                    "name": name or country_name_from_code(code) or code,
                    "observed_count": 0,
                },
            )
            current["observed_count"] = int(current["observed_count"]) + max(int(observed_count or 0), 0)
            if name and (not current["name"] or current["name"] == current["code"]):
                current["name"] = name
    except Exception:
        return []

    return sorted(
        counts.values(),
        key=lambda item: (-int(item["observed_count"]), str(item["name"]).lower(), str(item["code"])),
    )


def _build_observed_provider_values_payload(db: Optional[Session] = None) -> List[dict[str, Any]]:
    from app.providers.registry import list_provider_statuses

    observed_counts: dict[str, int] = {}
    if db is not None:
        try:
            observed_counts = {
                value: max(int(observed_count or 0), 0)
                for value, observed_count in _query_observed_provider_counts(db)
            }
        except Exception:
            observed_counts = {}

    values = []
    for item in list_provider_statuses():
        provider = " ".join(str(item.get("provider") or "").split()).lower()
        if not provider or item.get("display_enabled") is not True:
            continue
        label = " ".join(str((item.get("attribution") or {}).get("label") or provider).split()) or provider
        values.append(
            {
                "value": provider,
                "label": label,
                "observed_count": int(observed_counts.get(provider, 0)),
                "display_enabled": True,
            }
        )

    return sorted(values, key=lambda item: (-int(item["observed_count"]), item["label"].lower(), item["value"]))


def _build_observed_company_values_payload(db: Optional[Session] = None) -> List[dict[str, Any]]:
    counts: dict[str, int] = {}

    if db is not None:
        try:
            for value, observed_count in _query_observed_company_counts(db):
                counts[value] = counts.get(value, 0) + max(int(observed_count or 0), 0)
        except Exception:
            counts = {}

    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower(), item[0]))
    return [
        {"value": value, "observed_count": observed_count}
        for value, observed_count in ordered
    ]


def _build_jobs_filter_metadata_payload(db: Optional[Session] = None) -> dict[str, Any]:
    category_groups = _build_category_groups_payload()
    category_aliases = _build_category_aliases_payload()
    category_values = _build_observed_category_values_payload(db)
    level_values = _build_observed_level_values_payload(db)
    country_values = _build_observed_country_values_payload(db)
    provider_values = _build_observed_provider_values_payload(db)
    company_values = _build_observed_company_values_payload(db)
    levels = [item["label"] for item in level_values]

    core_payload = {
        "category_groups": category_groups,
        "category_aliases": category_aliases,
        "category_values": category_values,
        "level_values": level_values,
        "country_values": country_values,
        "provider_values": provider_values,
        "company_values": company_values,
        "levels": levels,
        "location_param_cap": max(1, settings.MUSE_LOCATION_PARAM_CAP),
    }
    metadata_raw = json.dumps(core_payload, sort_keys=True, separators=(",", ":"))
    metadata_hash = hashlib.sha256(metadata_raw.encode("utf-8")).hexdigest()

    return {
        **core_payload,
        "metadata_version": "jobs-filter-v2",
        "metadata_hash": metadata_hash,
    }


def _parse_posted_after_input(raw_value: Optional[str]) -> Optional[datetime]:
    value = (raw_value or "").strip()
    if not value:
        return None

    try:
        if "T" in value:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)

        parsed_date = datetime.strptime(value, "%Y-%m-%d")
        return parsed_date.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _parse_publication_datetime(raw_value: Optional[str]) -> Optional[datetime]:
    value = (raw_value or "").strip()
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _job_matches_keyword(mapped_job: dict[str, Any], keyword: str) -> bool:
    query = _normalize_text(keyword)
    if not query:
        return True

    searchable_chunks: List[str] = [
        mapped_job.get("name", "") or "",
        mapped_job.get("short_name", "") or "",
        mapped_job.get("company", "") or "",
        mapped_job.get("contents", "") or "",
        " ".join(mapped_job.get("locations", []) or []),
        " ".join(mapped_job.get("categories", []) or []),
        " ".join(mapped_job.get("levels", []) or []),
        " ".join(mapped_job.get("tags", []) or []),
    ]
    searchable = _normalize_text(" ".join(searchable_chunks))
    return query in searchable


def _job_matches_posted_after(mapped_job: dict[str, Any], posted_after: Optional[datetime]) -> bool:
    if posted_after is None:
        return True

    published_at = _parse_publication_datetime(mapped_job.get("publication_date"))
    if published_at is None:
        return False
    return published_at >= posted_after


def _extract_timezone_families(text: str) -> List[str]:
    families: List[str] = []
    for token in TIMEZONE_TOKEN_PATTERN.findall(text or ""):
        family = TIMEZONE_FAMILY_ALIASES.get((token or "").strip().lower())
        if family and family not in families:
            families.append(family)
    return families


def _extract_state_code(location_name: str) -> Optional[str]:
    if not location_name:
        return None

    state_match = re.search(r",\s*([A-Z]{2})(?:\s*,|\s*$)", location_name)
    if state_match:
        return state_match.group(1).upper()
    return None


def _extract_selected_timezone_families(selected_locations: List[str]) -> List[str]:
    found: List[str] = []
    for location_name in selected_locations:
        state_code = _extract_state_code(location_name)
        if not state_code:
            continue

        family = US_STATE_TO_TIMEZONE_FAMILY.get(state_code)
        if family and family not in found:
            found.append(family)

    return found


def _split_constraint_terms(raw_segment: str) -> List[str]:
    terms: List[str] = []
    for chunk in re.split(r",|\band\b|\bor\b|\bbut\b", raw_segment or "", flags=re.IGNORECASE):
        normalized = _normalize_constraint_text(chunk)
        normalized = re.sub(r"\b(the|metro|area|region|candidates|candidate|residing|within|in)\b", " ", normalized)
        normalized = _normalize_constraint_text(normalized)
        if not normalized or len(normalized) < 3:
            continue
        if normalized not in terms:
            terms.append(normalized)
    return terms


def _confidence_meets_threshold(confidence: str, threshold: str) -> bool:
    return CONSTRAINT_CONFIDENCE_RANK.get((confidence or "").lower(), 0) >= CONSTRAINT_CONFIDENCE_RANK.get((threshold or "").lower(), 2)


def _extract_location_constraints(job: dict, location_names: List[str]) -> dict[str, Any]:
    raw_text = " ".join(
        [
            job.get("name", "") or "",
            job.get("short_name", "") or "",
            job.get("contents", "") or "",
            " ".join(location_names),
        ]
    )
    clean_text = re.sub(r"<[^>]+>", " ", raw_text)
    normalized_text = _normalize_constraint_text(clean_text)

    include_timezone_families = _extract_timezone_families(clean_text)
    include_location_terms: List[str] = []
    exclude_location_terms: List[str] = []

    if "within the us" in normalized_text or "residing in the us" in normalized_text or "united states" in normalized_text:
        include_location_terms.append("united states")

    include_match = re.search(r"(?:residing\s+in|located\s+in|within)\s+([^.;\n]+)", clean_text, flags=re.IGNORECASE)
    if include_match:
        for term in _split_constraint_terms(include_match.group(1)):
            if term not in include_location_terms:
                include_location_terms.append(term)

    for segment in EXCLUSION_SEGMENT_PATTERN.findall(clean_text):
        for term in _split_constraint_terms(segment):
            if term not in exclude_location_terms:
                exclude_location_terms.append(term)

    for segment in EXCLUSION_INLINE_PATTERN.findall(clean_text):
        for term in _split_constraint_terms(segment):
            if term not in exclude_location_terms:
                exclude_location_terms.append(term)

    constraint_count = len(include_timezone_families) + len(include_location_terms) + len(exclude_location_terms)
    if constraint_count >= 2:
        confidence = "high"
    elif constraint_count == 1:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "include_timezone_families": include_timezone_families,
        "include_location_terms": include_location_terms,
        "exclude_location_terms": exclude_location_terms[:8],
        "confidence": confidence,
    }


def _term_matches_selected_locations(term: str, selected_locations: List[str], selected_country_code: str) -> bool:
    normalized_term = _normalize_constraint_text(term)
    if not normalized_term:
        return False

    selected_states = {
        (_extract_state_code(selected) or "").upper()
        for selected in selected_locations
        if _extract_state_code(selected)
    }

    for alias, alias_states in METRO_ALIAS_STATES.items():
        if alias in normalized_term and selected_states.intersection(alias_states):
            return True

    if normalized_term in {"us", "usa", "united states"}:
        return selected_country_code.upper() == "US"

    term_tokens = {tok for tok in re.split(r"[^a-z0-9]+", normalized_term) if tok}
    if not term_tokens:
        return False

    for selected in selected_locations:
        selected_tokens = {tok for tok in re.split(r"[^a-z0-9]+", _normalize_constraint_text(selected)) if tok}
        if term_tokens.issubset(selected_tokens) or selected_tokens.issubset(term_tokens):
            return True
    return False


def _evaluate_local_compatibility(
    *,
    constraints: dict[str, Any],
    selected_locations: List[str],
    selected_country_code: str,
) -> tuple[bool, str]:
    if not selected_locations:
        return False, "no-selected-locations"

    include_terms = constraints.get("include_location_terms") or []
    exclude_terms = constraints.get("exclude_location_terms") or []
    include_tz = constraints.get("include_timezone_families") or []
    selected_tz = _extract_selected_timezone_families(selected_locations)

    if include_terms:
        include_overlap = any(_term_matches_selected_locations(term, selected_locations, selected_country_code) for term in include_terms)
        if not include_overlap:
            return False, "include-location-miss"

    if include_tz:
        if not selected_tz:
            return False, "include-timezone-unknown"
        tz_overlap = bool(set(include_tz) & set(selected_tz))
        if not tz_overlap:
            return False, "include-timezone-miss"

    for term in exclude_terms:
        if _term_matches_selected_locations(term, selected_locations, selected_country_code):
            return False, "excluded-location-overlap"

    if not include_terms and not include_tz and not exclude_terms:
        return False, "no-constraints"

    return True, "constraint-overlap"


def _jobs_cache_enabled() -> bool:
    return settings.JOBS_CACHE_ENABLED and settings.JOBS_CACHE_TTL_SECONDS > 0


def _clone_cache_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(payload))


def _build_jobs_filter_signature(
    *,
    expanded_categories: List[str],
    normalized_levels: List[str],
    selected_locations: List[str],
    normalized_companies: List[str],
    include_remote: bool,
    include_hybrid: bool,
    location_mode: str,
    location_country_code: str,
    keyword_query: str,
    posted_after_iso: str,
    page_size: int,
) -> str:
    signature_payload = {
        "categories": expanded_categories,
        "levels": normalized_levels,
        "locations": selected_locations,
        "companies": normalized_companies,
        "include_remote": include_remote,
        "include_hybrid": include_hybrid,
        "location_mode": location_mode,
        "location_country_code": location_country_code,
        "keyword_query": keyword_query,
        "posted_after_iso": posted_after_iso,
        "page_size": page_size,
    }
    raw = json.dumps(signature_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cleanup_jobs_cache(now: float) -> None:
    expired_keys = [key for key, item in _JOBS_CACHE.items() if float(item.get("expires_at", 0)) <= now]
    for key in expired_keys:
        _JOBS_CACHE.pop(key, None)

    max_keys = max(10, settings.JOBS_CACHE_MAX_KEYS)
    if len(_JOBS_CACHE) <= max_keys:
        return

    ordered = sorted(_JOBS_CACHE.items(), key=lambda item: float(item[1].get("last_access", 0)))
    for key, _ in ordered[: len(_JOBS_CACHE) - max_keys]:
        _JOBS_CACHE.pop(key, None)


def _get_jobs_cache_response(signature: str, page: int) -> Optional[dict[str, Any]]:
    if not _jobs_cache_enabled():
        return None

    now = time.monotonic()
    _cleanup_jobs_cache(now)

    entry = _JOBS_CACHE.get(signature)
    if not entry:
        return None

    pages = entry.get("pages") or {}
    cached = pages.get(page)
    if not cached:
        return None

    entry["last_access"] = now
    response = _clone_cache_payload(cached)
    response["cache_hit"] = True
    return response


def _set_jobs_cache_response(signature: str, page: int, response_payload: dict[str, Any]) -> None:
    if not _jobs_cache_enabled():
        return

    now = time.monotonic()
    _cleanup_jobs_cache(now)

    ttl = max(1, settings.JOBS_CACHE_TTL_SECONDS)
    entry = _JOBS_CACHE.get(signature)
    if entry is None:
        entry = {
            "expires_at": now + ttl,
            "last_access": now,
            "pages": {},
        }
        _JOBS_CACHE[signature] = entry

    entry["expires_at"] = now + ttl
    entry["last_access"] = now
    entry.setdefault("pages", {})[page] = _clone_cache_payload(response_payload)


def _jobs_url_validation_enabled() -> bool:
    return (
        settings.JOBS_URL_VALIDATION_ENABLED
        and settings.JOBS_URL_VALIDATION_MAX_CHECKS_PER_REQUEST > 0
        and settings.JOBS_URL_VALIDATION_TIMEOUT_SECONDS > 0
    )


def _normalize_job_url_cache_key(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    normalized_path = parsed.path or "/"
    normalized_query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{normalized_path}{normalized_query}"


def _is_muse_landing_job_url(url: str | None) -> bool:
    parsed = urlparse((url or "").strip())
    host = (parsed.netloc or "").strip().lower()
    if host not in {"www.themuse.com", "themuse.com"}:
        return False
    path = (parsed.path or "").strip().lower()
    return path.startswith("/jobs/")


def _cleanup_job_url_validation_cache(now: float) -> None:
    expired_keys = [
        key for key, item in _JOB_URL_VALIDATION_CACHE.items()
        if float(item.get("expires_at", 0.0)) <= now
    ]
    for key in expired_keys:
        _JOB_URL_VALIDATION_CACHE.pop(key, None)

    max_keys = max(100, settings.JOBS_CACHE_MAX_KEYS * 4)
    if len(_JOB_URL_VALIDATION_CACHE) <= max_keys:
        return

    ordered = sorted(
        _JOB_URL_VALIDATION_CACHE.items(),
        key=lambda item: float(item[1].get("last_access", 0.0)),
    )
    for key, _ in ordered[: len(_JOB_URL_VALIDATION_CACHE) - max_keys]:
        _JOB_URL_VALIDATION_CACHE.pop(key, None)


def _get_job_url_validation_cache_verdict(url: str) -> Optional[str]:
    now = time.monotonic()
    _cleanup_job_url_validation_cache(now)
    key = _normalize_job_url_cache_key(url)
    if not key:
        return None
    entry = _JOB_URL_VALIDATION_CACHE.get(key)
    if not entry:
        return None
    if float(entry.get("expires_at", 0.0)) <= now:
        _JOB_URL_VALIDATION_CACHE.pop(key, None)
        return None
    entry["last_access"] = now
    verdict = str(entry.get("verdict") or "").strip().lower()
    return verdict or None


def _set_job_url_validation_cache_verdict(url: str, verdict: str) -> None:
    key = _normalize_job_url_cache_key(url)
    if not key:
        return

    normalized_verdict = (verdict or "").strip().lower()
    if normalized_verdict == "bad":
        ttl = max(1, int(settings.JOBS_URL_VALIDATION_BAD_TTL_SECONDS))
    elif normalized_verdict == "good":
        ttl = max(1, int(settings.JOBS_URL_VALIDATION_GOOD_TTL_SECONDS))
    else:
        normalized_verdict = "unknown"
        ttl = max(1, int(settings.JOBS_URL_VALIDATION_UNKNOWN_TTL_SECONDS))

    now = time.monotonic()
    _cleanup_job_url_validation_cache(now)
    _JOB_URL_VALIDATION_CACHE[key] = {
        "verdict": normalized_verdict,
        "expires_at": now + ttl,
        "last_access": now,
    }


def _is_job_not_found_signature(body_text: str | None) -> bool:
    normalized = (body_text or "").strip().lower()
    if not normalized:
        return False
    return "job not found" in normalized and "could not be found" in normalized


def _classify_job_url_validation_verdict(status_code: int, body_text: str | None) -> str:
    if status_code in INVALID_JOB_URL_STATUSES:
        return "bad"
    if _is_job_not_found_signature(body_text):
        return "bad"
    if 200 <= status_code < 400:
        return "good"
    return "unknown"


async def _validate_candidate_job_urls(
    candidates: List[tuple[dict[str, Any], str]],
    *,
    url_client: Optional[httpx.AsyncClient],
    remaining_checks: int,
) -> tuple[List[tuple[dict[str, Any], str]], dict[str, int]]:
    stats = {
        "checked_count": 0,
        "cache_hit_count": 0,
        "request_count": 0,
        "dropped_count": 0,
    }
    if not candidates or remaining_checks <= 0 or not _jobs_url_validation_enabled() or url_client is None:
        return candidates, stats

    semaphore = asyncio.Semaphore(max(1, int(settings.JOBS_URL_VALIDATION_CONCURRENCY)))
    checked_slots = 0
    cached_verdicts: dict[int, str] = {}
    pending: List[tuple[int, str]] = []
    pending_by_key: dict[str, list[int]] = {}

    for index, (mapped, _reason) in enumerate(candidates):
        job_url = (mapped.get("job_url") or "").strip()
        if not _is_muse_landing_job_url(job_url):
            continue

        key = _normalize_job_url_cache_key(job_url)
        if not key:
            continue

        if key in pending_by_key:
            pending_by_key[key].append(index)
            continue

        cached_verdict = _get_job_url_validation_cache_verdict(job_url)
        if cached_verdict is not None:
            cached_verdicts[index] = cached_verdict
            stats["checked_count"] += 1
            stats["cache_hit_count"] += 1
            continue

        if checked_slots >= remaining_checks:
            continue

        checked_slots += 1
        pending_by_key[key] = [index]
        pending.append((index, job_url))

    async def _request_verdict(url: str) -> str:
        async with semaphore:
            try:
                response = await url_client.get(url)
                body_preview = (response.text or "")[:6000]
            except Exception:
                return "unknown"
            return _classify_job_url_validation_verdict(response.status_code, body_preview)

    request_results: dict[int, str] = {}
    if pending:
        verdicts = await asyncio.gather(*[_request_verdict(url) for _index, url in pending], return_exceptions=True)
        for (index, job_url), verdict in zip(pending, verdicts):
            resolved = verdict if isinstance(verdict, str) else "unknown"
            request_results[index] = resolved
            stats["checked_count"] += 1
            stats["request_count"] += 1
            _set_job_url_validation_cache_verdict(job_url, resolved)

            cache_key = _normalize_job_url_cache_key(job_url)
            related_indexes = pending_by_key.get(cache_key, [])
            for related_index in related_indexes:
                request_results[related_index] = resolved

    filtered: List[tuple[dict[str, Any], str]] = []
    for index, candidate in enumerate(candidates):
        verdict = request_results.get(index) or cached_verdicts.get(index)
        if verdict == "bad":
            stats["dropped_count"] += 1
            continue
        filtered.append(candidate)

    return filtered, stats


def _strip_location_params(params_base: List[tuple[str, str]]) -> List[tuple[str, str]]:
    return [item for item in params_base if item[0] != "location"]


def _should_run_location_relaxed_fallback(
    *,
    page: int,
    accepted_jobs_count: int,
    selected_locations: List[str],
    location_relaxed_fallback: bool,
) -> bool:
    if location_relaxed_fallback:
        return False
    if page != 1:
        return False
    if accepted_jobs_count > 0:
        return False
    return len(selected_locations) > 0


def _is_remote_location_name(name: Optional[str]) -> bool:
    normalized = _normalize_text(name)
    if not normalized:
        return False

    return (
        "remote" in normalized
        or "work from home" in normalized
        or "telecommute" in normalized
        or normalized == "anywhere"
    )


def _is_flexible_or_remote_location_name(name: Optional[str]) -> bool:
    normalized = _normalize_text(name)
    if not normalized:
        return False
    return (
        _is_remote_location_name(normalized)
        or "hybrid" in normalized
        or "flexible" in normalized
    )


def _location_matches_selected(location_name: str, selected_locations: List[str]) -> bool:
    normalized_location = _normalize_text(location_name)
    if not normalized_location:
        return False

    location_tokens = [token for token in re.split(r"[^a-z0-9]+", normalized_location) if token]
    location_token_set = set(location_tokens)

    for selected in selected_locations:
        normalized_selected = _normalize_text(selected)
        if not normalized_selected:
            continue
        selected_tokens = [token for token in re.split(r"[^a-z0-9]+", normalized_selected) if token]
        if not selected_tokens:
            continue

        selected_token_set = set(selected_tokens)
        if selected_token_set.issubset(location_token_set):
            return True

        # Also allow an exact normalized match when tokenization is too strict for edge cases.
        if normalized_selected == normalized_location:
            return True

    return False


def _normalize_location_key(value: Optional[str]) -> str:
    return " ".join((value or "").strip().split()).lower()


def _location_tokens(value: Optional[str]) -> set[str]:
    normalized = _normalize_location_key(value)
    if not normalized:
        return set()
    return {token for token in re.split(r"[^a-z0-9]+", normalized) if token}


def _choose_best_supported_location(
    raw_location: str,
    candidates: List[MuseSupportedLocation],
    preferred_state_code: Optional[str] = None,
) -> tuple[Optional[str], bool]:
    raw_tokens = _location_tokens(raw_location)
    if not candidates:
        return None, False

    filtered_candidates = candidates
    matched_preferred_state = False
    if preferred_state_code:
        preferred_state = preferred_state_code.strip().upper()
        state_filtered = [
            row for row in candidates
            if (_extract_state_code(row.location_name) or "").upper() == preferred_state
        ]
        if state_filtered:
            filtered_candidates = state_filtered
            matched_preferred_state = True
        else:
            return None, False

    best: Optional[MuseSupportedLocation] = None
    best_score: tuple[int, int, int] = (-1, -1, -1)
    for row in filtered_candidates:
        candidate_tokens = _location_tokens(row.location_name)
        overlap = len(raw_tokens & candidate_tokens)
        observed_count = int(row.observed_count or 0)
        token_similarity = -abs(len(candidate_tokens) - len(raw_tokens))
        score = (overlap, observed_count, token_similarity)

        if score > best_score:
            best = row
            best_score = score

    if best is None:
        return None, False
    return best.location_name, matched_preferred_state


def _canonicalize_selected_locations(
    *,
    raw_locations: List[str],
    location_mode: Optional[str],
    location_country_code: Optional[str],
    location_param_cap: int,
    db: Session,
) -> tuple[List[str], dict[str, Any]]:
    normalized_raw = []
    seen_raw = set()
    for raw in raw_locations:
        clean = " ".join((raw or "").strip().split())
        if not clean:
            continue
        key = clean.lower()
        if key in seen_raw:
            continue
        seen_raw.add(key)
        normalized_raw.append(clean)

    if not normalized_raw:
        return [], {
            "canonicalized_count": 0,
            "transformed_count": 0,
            "unmatched_count": 0,
            "requested_unique_count": 0,
            "dropped_count": 0,
            "dropped_locations_sample": [],
            "strategy": "none",
            "country_scope": (location_country_code or "").upper(),
        }

    scope_country = (location_country_code or "").strip().upper()
    query = db.query(MuseSupportedLocation).filter(MuseSupportedLocation.active.is_(True))
    if scope_country:
        query = query.filter(MuseSupportedLocation.country_code == scope_country)

    supported_rows = query.all()
    if not supported_rows:
        selected = normalized_raw[:location_param_cap]
        dropped_locations = normalized_raw[location_param_cap:]
        return selected, {
            "canonicalized_count": len(selected),
            "transformed_count": 0,
            "unmatched_count": len(selected),
            "requested_unique_count": len(normalized_raw),
            "dropped_count": max(0, len(normalized_raw) - len(selected)),
            "dropped_locations_sample": dropped_locations[:12],
            "strategy": "raw-fallback-no-index",
            "country_scope": scope_country,
        }

    by_exact_key: dict[str, MuseSupportedLocation] = {}
    by_city_key: dict[str, list[MuseSupportedLocation]] = {}

    for row in supported_rows:
        exact_key = _normalize_location_key(row.location_name)
        existing_exact = by_exact_key.get(exact_key)
        if existing_exact is None or int(row.observed_count or 0) > int(existing_exact.observed_count or 0):
            by_exact_key[exact_key] = row

        city_key = exact_key.split(",")[0].strip()
        if city_key:
            by_city_key.setdefault(city_key, []).append(row)

    resolved_candidates: List[dict[str, Any]] = []
    selected_seen = set()
    transformed_count = 0
    unmatched_count = 0
    strict_state_blocked_count = 0
    normalized_mode = (location_mode or "").strip().lower()
    strict_state_mode = normalized_mode in {"nearby", "manual"} and scope_country == "US"

    for raw_index, raw in enumerate(normalized_raw):
        raw_key = _normalize_location_key(raw)
        resolved = None
        match_type = "raw-fallback"
        raw_state = _extract_state_code(raw)

        exact_row = by_exact_key.get(raw_key)
        if exact_row is not None:
            resolved = exact_row.location_name
            match_type = "exact"
        else:
            city_key = raw_key.split(",")[0].strip()
            candidates = by_city_key.get(city_key, []) if city_key else []
            preferred_state = raw_state if strict_state_mode and raw_state else None
            resolved, matched_preferred_state = _choose_best_supported_location(
                raw,
                candidates,
                preferred_state_code=preferred_state,
            )
            if resolved:
                match_type = "city-fallback-state" if matched_preferred_state else "city-fallback"
            elif preferred_state:
                strict_state_blocked_count += 1

        if not resolved:
            resolved = raw
            unmatched_count += 1
        elif _normalize_location_key(resolved) != raw_key:
            transformed_count += 1

        resolved_key = resolved.lower()
        if resolved_key in selected_seen:
            continue
        selected_seen.add(resolved_key)

        resolved_candidates.append(
            {
                "resolved": resolved,
                "raw_index": raw_index,
                "match_type": match_type,
                "state_code": _extract_state_code(resolved) or "",
            }
        )

    ordered_candidates = sorted(
        resolved_candidates,
        key=lambda item: (
            item["raw_index"],
            0 if item["match_type"] == "exact" else 1,
        ),
    )

    selected_locations: List[str] = []
    if strict_state_mode:
        by_state: dict[str, List[dict[str, Any]]] = {}
        for item in ordered_candidates:
            state_key = item["state_code"] or "__none__"
            by_state.setdefault(state_key, []).append(item)

        ordered_states = sorted(
            by_state.keys(),
            key=lambda state: min(entry["raw_index"] for entry in by_state[state]),
        )

        while len(selected_locations) < location_param_cap:
            advanced = False
            for state in ordered_states:
                bucket = by_state[state]
                if not bucket:
                    continue
                selected_locations.append(bucket.pop(0)["resolved"])
                advanced = True
                if len(selected_locations) >= location_param_cap:
                    break
            if not advanced:
                break
    else:
        selected_locations = [item["resolved"] for item in ordered_candidates[:location_param_cap]]

    dropped_locations = [item["resolved"] for item in ordered_candidates[len(selected_locations):]]

    return selected_locations, {
        "canonicalized_count": len(selected_locations),
        "transformed_count": transformed_count,
        "unmatched_count": unmatched_count,
        "strict_state_blocked_count": strict_state_blocked_count,
        "state_diversity_count": len({(_extract_state_code(name) or "") for name in selected_locations if _extract_state_code(name)}),
        "requested_unique_count": len(normalized_raw),
        "dropped_count": max(0, len(ordered_candidates) - len(selected_locations)),
        "dropped_locations_sample": dropped_locations[:12],
        "strategy": "muse-index-country-aware-nearby-state-locked" if strict_state_mode else ("muse-index-country-aware" if scope_country else "muse-index-global"),
        "country_scope": scope_country,
    }


def _has_concrete_selected_location(job_locations: List[str], selected_locations: List[str]) -> bool:
    if not selected_locations:
        return True

    for location_name in job_locations:
        if _is_flexible_or_remote_location_name(location_name):
            continue
        if _location_matches_selected(location_name, selected_locations):
            return True

    return False


def _classify_job_work_mode(job: dict) -> tuple[bool, bool, str]:
    raw_locations = job.get("locations", []) or []
    location_names = [loc.get("name", "") for loc in raw_locations if isinstance(loc, dict)]
    has_remote_location = any(_is_remote_location_name(name) for name in location_names)

    searchable_text = " ".join(
        [
            job.get("name", "") or "",
            job.get("short_name", "") or "",
            job.get("contents", "") or "",
        ]
    )

    has_hybrid_location = any("hybrid" in _normalize_text(name) for name in location_names)
    has_hybrid_text = bool(HYBRID_TEXT_PATTERN.search(searchable_text))
    has_remote_text = bool(REMOTE_TEXT_PATTERN.search(searchable_text))

    has_hybrid = has_hybrid_location or has_hybrid_text
    has_remote = has_remote_location or has_remote_text

    if has_hybrid_location:
        reason = "location-name-hybrid"
    elif has_hybrid_text:
        reason = "text-hybrid"
    elif has_remote_location:
        reason = "location-name-remote"
    elif has_remote_text:
        reason = "text-remote"
    else:
        reason = "none"

    return has_remote, has_hybrid, reason


def _is_job_allowed_by_preferences(
    *,
    has_remote: bool,
    has_hybrid: bool,
    include_remote: bool,
    include_hybrid: bool,
    job_locations: List[str],
    selected_locations: List[str],
    allow_local_compatible_remote: bool,
) -> tuple[bool, str]:
    has_concrete_location_match = _has_concrete_selected_location(job_locations, selected_locations)
    if selected_locations and not has_concrete_location_match:
        # When toggles are enabled, allow remote/hybrid jobs even without a concrete nearby-city match.
        if include_remote and has_remote:
            reason = "remote_override"
        elif include_hybrid and has_hybrid:
            reason = "hybrid_override"
        else:
            return False, "no-match"
    else:
        reason = "concrete_location" if selected_locations else "no-location-filter"

    is_remote_only = has_remote and not has_hybrid
    if not include_hybrid and has_hybrid:
        return False, "hybrid-disabled"
    if not include_remote and is_remote_only and not allow_local_compatible_remote:
        return False, "remote-disabled"
    return True, reason


def _normalize_level_for_muse(level_value: str) -> str:
    normalized = (level_value or "").strip()
    if normalized.lower() == "management":
        return "management"
    return normalized


def _expand_category_for_muse(raw_value: str) -> List[str]:
    value = (raw_value or "").strip()
    if not value:
        return []

    key = value.lower()
    canonical_group = CATEGORY_GROUP_ALIAS.get(key, key)
    expanded = UNIFIED_CATEGORY_GROUPS.get(canonical_group)
    if expanded:
        return expanded

    return [value]


def _map_muse_job(job: dict) -> dict:
    has_remote, has_hybrid, work_mode_reason = _classify_job_work_mode(job)
    locations = [loc.get("name") for loc in job.get("locations", []) if loc.get("name")]
    company = job.get("company") or {}

    location_mode_flags = []
    if has_remote:
        location_mode_flags.append("remote")
    if has_hybrid:
        location_mode_flags.append("hybrid")
    constraints = _extract_location_constraints(job, locations)

    return {
        "id": job.get("id"),
        "provider": "the_muse",
        "provider_job_id": str(job.get("id") or ""),
        "name": job.get("name"),
        "title": job.get("name"),
        "short_name": job.get("short_name"),
        "type": job.get("type"),
        "model_type": job.get("model_type"),
        "company": company.get("name"),
        "company_id": company.get("id"),
        "company_short_name": company.get("short_name"),
        "locations": locations,
        "all_location_names": locations,
        "levels": [lvl.get("name") for lvl in job.get("levels", []) if lvl.get("name")],
        "categories": [cat.get("name") for cat in job.get("categories", []) if cat.get("name")],
        "tags": [tag.get("name") for tag in job.get("tags", []) if tag.get("name")],
        "has_remote": has_remote,
        "has_hybrid": has_hybrid,
        "location_mode_flags": location_mode_flags,
        "work_mode_reason": work_mode_reason,
        "location_constraints": constraints,
        "publication_date": job.get("publication_date"),
        "job_url": job.get("refs", {}).get("landing_page"),
        "contents": job.get("contents") or "",
    }


def _normalize_saved_job_legacy_id(raw_value: str | None) -> int | None:
    normalized = " ".join(str(raw_value or "").split())
    if not normalized or not normalized.isdigit():
        return None
    return int(normalized)


def _find_existing_saved_job(
    db: Session,
    *,
    user_id: int,
    provider: str | None,
    provider_job_id: str,
    legacy_job_id: int | None,
) -> SavedJob | None:
    existing_job = None
    if provider and provider_job_id:
        existing_job = (
            db.query(SavedJob)
            .filter(
                SavedJob.user_id == user_id,
                SavedJob.provider == provider,
                SavedJob.provider_job_id == provider_job_id,
            )
            .first()
        )

    if existing_job is None and legacy_job_id is not None:
        existing_job = (
            db.query(SavedJob)
            .filter(
                SavedJob.user_id == user_id,
                SavedJob.job_id == legacy_job_id,
            )
            .first()
        )

    if existing_job is None and not provider and provider_job_id:
        existing_job = (
            db.query(SavedJob)
            .filter(
                SavedJob.user_id == user_id,
                SavedJob.provider_job_id == provider_job_id,
            )
            .first()
        )

    return existing_job


def _serialize_saved_job_row(saved_job: SavedJob, db: Session) -> dict[str, Any]:
    from app.models.job import Job
    from app.services.job_search import _serialize_job as serialize_local_job

    current_job = None
    if saved_job.provider and saved_job.provider_job_id:
        current_job = (
            db.query(Job)
            .filter(
                Job.provider == saved_job.provider,
                Job.provider_job_id == saved_job.provider_job_id,
            )
            .order_by(Job.last_seen_at.desc().nullslast(), Job.first_seen_at.desc().nullslast())
            .first()
        )

    if current_job is not None:
        payload = serialize_local_job(current_job)
        payload["saved_job_id"] = saved_job.id
        payload["saved_at"] = saved_job.created_at.isoformat() if saved_job.created_at else None
        payload["provider"] = payload.get("provider") or (saved_job.provider or "")
        payload["provider_job_id"] = payload.get("provider_job_id") or (
            saved_job.provider_job_id or (str(saved_job.job_id) if saved_job.job_id is not None else "")
        )
        if not payload.get("apply_url"):
            payload["apply_url"] = saved_job.url
        if not payload.get("job_url"):
            payload["job_url"] = saved_job.url
        return payload

    provider_job_id = saved_job.provider_job_id or (
        str(saved_job.job_id) if saved_job.job_id is not None else f"saved-{saved_job.id}"
    )
    saved_at = saved_job.created_at.isoformat() if saved_job.created_at else None
    return {
        "local_id": f"saved-{saved_job.id}",
        "id": provider_job_id,
        "saved_job_id": saved_job.id,
        "saved_at": saved_at,
        "provider": saved_job.provider or "",
        "provider_job_id": provider_job_id,
        "provider_url": saved_job.url,
        "provider_url_status": "unknown",
        "job_url": saved_job.url,
        "apply_url": saved_job.url,
        "apply_url_status": "unknown",
        "apply_portal": "saved_snapshot",
        "source_tags": ["saved_snapshot"],
        "title": saved_job.title,
        "name": saved_job.title,
        "short_name": saved_job.title,
        "company": saved_job.company,
        "company_url": None,
        "location": "",
        "location_country_code": "",
        "location_country_name": "",
        "locations": [],
        "job_type": "",
        "type": "",
        "experience_level": "",
        "levels": [],
        "categories": [],
        "tags": [],
        "short_description": "",
        "description": "",
        "contents": "",
        "is_remote": False,
        "has_remote": False,
        "has_hybrid": False,
        "quality_score": 0.0,
        "display_tier": "saved",
        "staleness_status": "unknown",
        "staleness_flags": [],
        "published_at": None,
        "publication_date": None,
        "is_featured": False,
        "is_active": True,
        "work_mode_reason": "unknown",
        "is_local_compatible_remote": False,
        "local_compatibility_reason": "",
    }


def _extract_client_ip(request: Request) -> Optional[str]:
    candidates: List[str] = []

    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        candidates.extend([part.strip() for part in forwarded.split(",") if part.strip()])

    real_ip = (request.headers.get("x-real-ip", "") or "").strip()
    if real_ip:
        candidates.append(real_ip)

    if request.client and request.client.host:
        candidates.append((request.client.host or "").strip())

    for candidate in candidates:
        try:
            ip_obj = ipaddress.ip_address(candidate)
            if ip_obj.is_global:
                return str(ip_obj)
        except ValueError:
            continue

    # Returning None tells providers to resolve by server egress IP.
    return None


@router.get(
    "/geolocation/ip",
    tags=["geolocation"],
    response_description="Resolved IP-based geolocation payload.",
    responses={
        200: {
            "description": "IP geolocation resolved successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "latitude": 34.7304,
                        "longitude": -86.5861,
                        "city": "Huntsville",
                        "country": "United States",
                        "country_code": "US",
                        "region": "Alabama",
                        "source": "ip-api",
                        "accuracy_km": 50,
                    }
                }
            },
        },
        502: {
            "description": "Upstream geolocation provider failed.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "GEO_IP_FAILED",
                            "message": "Could not determine location from IP.",
                            "debug": "provider timeout",
                        }
                    }
                }
            },
        },
    },
)
async def geolocation_by_ip(request: Request):
    """
    Resolve approximate user location from request IP address.

    Attempts to detect a public client IP from forwarding headers and socket
    metadata, then delegates to the geolocation provider.

    Response codes:
    - 200: IP geolocation resolved successfully.
    - 502: Upstream geolocation provider error.
    """
    client_ip = _extract_client_ip(request)
    try:
        payload = await resolve_ip_location(client_ip)
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "GEO_IP_FAILED",
                "message": "Could not determine location from IP.",
                "debug": str(exc),
            },
        )


@router.get(
    "/geolocation/geocode",
    tags=["geolocation"],
    response_description="Geocoded location candidate payload.",
    responses={
        200: {
            "description": "Geocoding succeeded.",
            "content": {
                "application/json": {
                    "example": {
                        "latitude": 34.7304,
                        "longitude": -86.5861,
                        "display_name": "Huntsville, Alabama, United States",
                        "city": "Huntsville",
                        "country": "United States",
                        "country_code": "US",
                    }
                }
            },
        },
        404: {
            "description": "Location could not be resolved.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "GEO_GEOCODE_FAILED",
                            "message": "Could not find that location. Try a city name or ZIP code.",
                            "debug": "no candidates",
                        }
                    }
                }
            },
        },
    },
)
async def geocode_location(
    q: str = Query(
        ...,
        min_length=2,
        max_length=200,
        description="Location search input such as city, state, postal code, or full place string.",
    ),
    country_code: Optional[str] = Query(
        None,
        min_length=2,
        max_length=2,
        description="Optional ISO-3166 country code to narrow geocoding candidates (for example, US, CA, GB).",
    ),
):
    """
    Convert free-text location input into normalized coordinates and metadata.

    Useful for turning user-entered location text into structured lat/lon
    values for job filtering and nearby-city discovery.

    Response codes:
    - 200: Location resolved successfully.
    - 404: No matching location found.
    """
    try:
        return await geocode_query(q, country_code=country_code)
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "GEO_GEOCODE_FAILED",
                "message": "Could not find that location. Try a city name or ZIP code.",
                "debug": str(exc),
            },
        )


@router.get(
    "/geolocation/reverse",
    tags=["geolocation"],
    response_description="Reverse-geocoded place payload.",
    responses={
        200: {
            "description": "Reverse geocoding succeeded.",
            "content": {
                "application/json": {
                    "example": {
                        "latitude": 34.7304,
                        "longitude": -86.5861,
                        "city": "Huntsville",
                        "region": "Alabama",
                        "country": "United States",
                        "country_code": "US",
                    }
                }
            },
        },
        502: {
            "description": "Reverse geocoding provider error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "code": "GEO_REVERSE_FAILED",
                            "message": "Could not resolve this coordinate into a place name.",
                            "debug": "provider unavailable",
                        }
                    }
                }
            },
        },
    },
)
async def reverse_geocode_location(
    latitude: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees. Valid range: -90 to 90."),
    longitude: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees. Valid range: -180 to 180."),
):
    """
    Convert coordinates into a human-readable place representation.

    Uses reverse geocoding to map latitude/longitude to city/region/country
    metadata for display and filtering workflows.

    Response codes:
    - 200: Reverse geocoding resolved successfully.
    - 502: Upstream reverse geocoder failure.
    """
    try:
        return await reverse_geocode(latitude, longitude)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "GEO_REVERSE_FAILED",
                "message": "Could not resolve this coordinate into a place name.",
                "debug": str(exc),
            },
        )


@router.get(
    "/geolocation/cities-in-radius",
    tags=["geolocation"],
    response_description="Cities that fall within the requested radius.",
    responses={
        200: {
            "description": "Radius search completed.",
            "content": {
                "application/json": {
                    "example": {
                        "cities": [
                            {"name": "Huntsville", "state": "AL", "country_code": "US", "distance_miles": 0.0},
                            {"name": "Madison", "state": "AL", "country_code": "US", "distance_miles": 11.2},
                        ],
                        "total_count": 2,
                        "radius_miles": 25.0,
                        "radius_km": 40.23,
                    }
                }
            },
        }
    },
)
async def cities_in_radius(
    latitude: float = Query(..., ge=-90, le=90, description="Center latitude for radius search in decimal degrees."),
    longitude: float = Query(..., ge=-180, le=180, description="Center longitude for radius search in decimal degrees."),
    radius: float = Query(25, gt=0, description="Radius value, interpreted by the selected unit"),
    unit: str = Query("mi", description="Distance unit for radius. Supported values: 'mi' (miles) or 'km' (kilometers)."),
    country_code: Optional[str] = Query(None, description="Optional ISO country code to constrain matches"),
    limit: int = Query(200, ge=1, le=500, description="Maximum number of city results to return after filtering."),
):
    """
    Find known cities within a radius of a coordinate point.

    Applies optional country constraints and returns both mile and kilometer
    representations of the effective search radius.

    Response codes:
    - 200: Search completed successfully (may return empty city list).
    """
    normalized_unit = (unit or "mi").strip().lower()
    radius_miles = km_to_miles(radius) if normalized_unit == "km" else radius
    radius_miles = min(radius_miles, 100.0)

    cities = find_cities_in_radius(
        latitude=latitude,
        longitude=longitude,
        radius_miles=radius_miles,
        country_code=country_code,
        limit=limit,
    )

    if not cities:
        return {
            "code": "GEO_RADIUS_EMPTY",
            "message": "No cities were found within this radius.",
            "debug": {
                "latitude": latitude,
                "longitude": longitude,
                "radius_miles": round(radius_miles, 2),
                "country_code": (country_code or "").upper(),
            },
            "cities": [],
            "total_count": 0,
            "radius_miles": round(radius_miles, 2),
            "radius_km": round(miles_to_km(radius_miles), 2),
        }

    return {
        "cities": cities,
        "total_count": len(cities),
        "radius_miles": round(radius_miles, 2),
        "radius_km": round(miles_to_km(radius_miles), 2),
    }


@router.get(
    "/geolocation/country-cities",
    tags=["geolocation"],
    response_description="Known city list for the requested country code.",
    responses={
        200: {
            "description": "Country-city lookup completed.",
            "content": {
                "application/json": {
                    "example": {
                        "cities": [
                            {"name": "Huntsville", "state": "AL", "country_code": "US"},
                            {"name": "Seattle", "state": "WA", "country_code": "US"},
                        ],
                        "total_count": 2,
                        "country_code": "US",
                    }
                }
            },
        }
    },
)
async def country_cities(
    country_code: str = Query(..., min_length=2, max_length=2, description="ISO country code"),
    limit: int = Query(120, ge=1, le=400, description="Maximum number of cities to include in response."),
):
    """
    List known cities for a specific country.

    Useful for pre-populating location selectors and narrowing job searches to
    specific geographies.

    Response codes:
    - 200: Country lookup completed (may return empty city list).
    """
    cities = list_country_cities(country_code=country_code, limit=limit)
    if not cities:
        return {
            "code": "GEO_COUNTRY_EMPTY",
            "message": "No known city data for that country yet.",
            "cities": [],
            "total_count": 0,
        }

    return {
        "cities": cities,
        "total_count": len(cities),
        "country_code": country_code.upper(),
    }


@router.get(
    "/geolocation/muse-supported-countries",
    tags=["geolocation"],
    response_description="Countries currently represented in the Muse location index.",
    responses={
        200: {
            "description": "Supported country set returned.",
            "content": {
                "application/json": {
                    "example": {
                        "countries": [
                            {"country_code": "US", "country_name": "United States", "location_count": 300},
                            {"country_code": "CA", "country_name": "Canada", "location_count": 40},
                        ],
                        "total_count": 2,
                    }
                }
            },
        }
    },
)
async def muse_supported_countries(db: Session = Depends(get_db)):
    """
    List countries currently covered by the indexed Muse location dataset.

    Ensures the location index is available and returns normalized country
    metadata used for downstream location canonicalization.

    Response codes:
    - 200: Supported countries returned successfully.
    """
    await ensure_muse_location_index()
    countries = list_supported_countries(db)
    return {
        "countries": countries,
        "total_count": len(countries),
    }


@router.get(
    "/geolocation/muse-supported-locations",
    tags=["geolocation"],
    response_description="Muse-supported location list for the selected country.",
    responses={
        200: {
            "description": "Supported locations returned.",
            "content": {
                "application/json": {
                    "example": {
                        "locations": [
                            {"location_name": "New York, NY", "country_code": "US", "active": True},
                            {"location_name": "Seattle, WA", "country_code": "US", "active": True},
                        ],
                        "total_count": 2,
                        "country_code": "US",
                    }
                }
            },
        }
    },
)
async def muse_supported_locations(
    country_code: str = Query(..., min_length=2, max_length=2, description="ISO country code"),
    limit: int = Query(200, ge=1, le=500, description="Maximum number of supported locations to return for the country."),
    db: Session = Depends(get_db),
):
    """
    List Muse-supported locations for a given country.

    Used to canonicalize user-provided location filters before querying Muse so
    searches remain consistent and higher quality.

    Response codes:
    - 200: Locations returned successfully (may be empty for unsupported country).
    """
    await ensure_muse_location_index()
    locations = list_supported_locations_for_country(db, country_code=country_code, limit=limit)
    if not locations:
        return {
            "code": "MUSE_COUNTRY_EMPTY",
            "message": "No Muse-supported locations were found for that country.",
            "locations": [],
            "total_count": 0,
            "country_code": country_code.upper(),
        }

    return {
        "locations": locations,
        "total_count": len(locations),
        "country_code": country_code.upper(),
    }


@router.post(
    "/geolocation/muse-supported-locations/refresh",
    tags=["geolocation"],
    response_description="Result of refresh operation plus high-level index counters.",
    responses={
        200: {
            "description": "Refresh completed.",
            "content": {
                "application/json": {
                    "example": {
                        "refresh": {"status": "refreshed", "records_upserted": 347, "duration_seconds": 5.8},
                        "countries_total": 12,
                    }
                }
            },
        }
    },
)
async def refresh_muse_supported_locations(
    force: bool = Query(False, description="When true, bypass freshness checks and force a full index refresh."),
    db: Session = Depends(get_db),
):
    """
    Refresh cached Muse location support index.

    Triggers an index refresh process and returns both refresh metadata and the
    updated count of supported countries.

    Response codes:
    - 200: Refresh completed or confirmed current index state.
    """
    result = await refresh_muse_location_index(force=force)
    countries = list_supported_countries(db)
    return {
        "refresh": result,
        "countries_total": len(countries),
    }


@router.get(
    "/jobs/filter-metadata",
    tags=["jobs"],
    response_description="Canonical category/level metadata and search guardrail limits for the Job Board.",
)
async def jobs_filter_metadata(db: Session = Depends(get_db)):
    """
    Return shared filter metadata consumed by the Job Board UI.

    Keeps category/level taxonomy and location parameter guardrail values in one
    backend-owned contract so frontend and backend behavior stay aligned.
    """
    return _build_jobs_filter_metadata_payload(db)

@router.get(
    "/jobs/search-live-source",
    tags=["jobs"],
    response_description="Filtered job results with diagnostics and pagination metadata.",
    responses={
        200: {
            "description": "Job search completed successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "ui_page": 1,
                        "page_size": 10,
                        "has_next_page": True,
                        "total_jobs_estimated": 21,
                        "jobs": [
                            {
                                "id": 12345,
                                "name": "Software Engineer",
                                "company": "Acme",
                                "locations": ["Huntsville, AL"],
                                "has_remote": False,
                                "has_hybrid": True,
                                "job_url": "https://www.themuse.com/jobs/acme/software-engineer",
                            }
                        ],
                        "source_pages_scanned": 2,
                        "filtered_out_count": 30,
                        "guardrail_stop_reason": "target_reached",
                    }
                }
            },
        },
        500: {
            "description": "Provider fetch failed on first source page.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to fetch jobs from The Muse API"
                    }
                }
            },
        },
    },
)
async def search_jobs(
    page: int = Query(1, ge=1, description="UI page number (1-indexed)."),
    page_size: int = Query(
        settings.JOBS_DEFAULT_PAGE_SIZE,
        ge=1,
        le=100,
        description="Number of jobs to return for the requested UI page. Max 100.",
    ),
    category: Optional[List[str]] = Query(
        None,
        description="One or more category labels. Values are expanded to Muse-compatible categories.",
    ),
    catogory: Optional[List[str]] = Query(
        None,
        description="Backward-compatible misspelled alias of category retained for existing clients.",
    ),
    level: Optional[List[str]] = Query(
        None,
        description="Experience levels such as internship, entry, mid, senior. Values are normalized for Muse.",
    ),
    location: Optional[List[str]] = Query(
        None,
        description="One or more location strings (city/state/country) to canonicalize and filter against.",
    ),
    location_mode: Optional[str] = Query(
        None,
        description="Location interpretation strategy hint. Common values: nearby, country, manual.",
    ),
    location_country_code: Optional[str] = Query(
        None,
        min_length=2,
        max_length=2,
        description="Optional ISO-3166 country code used to constrain location canonicalization.",
    ),
    company: Optional[List[str]] = Query(
        None,
        description="One or more company names to include in provider query filters.",
    ),
    q: Optional[str] = Query(
        None,
        min_length=1,
        max_length=200,
        description="Optional keyword query applied server-side across title, company, location, tags, and description.",
    ),
    posted_after: Optional[str] = Query(
        None,
        description="Optional ISO date or datetime filter. Only jobs published on/after this value are returned.",
    ),
    include_remote: bool = Query(True, description="When true, include fully remote roles that pass compatibility rules."),
    include_hybrid: bool = Query(True, description="When true, include hybrid roles in the result set."),
    db: Session = Depends(get_db),
):
    """
    Search and filter jobs from The Muse with local compatibility guardrails.

    This endpoint applies category/level/company filters, canonicalizes user
    location input, performs adaptive multi-page provider scanning, and enforces
    local policy preferences for remote/hybrid compatibility.

    The response includes diagnostics (source pages scanned, filtered counts,
    constraint confidence metrics, and pagination estimates) to support frontend
    transparency and debugging.

    Response codes:
    - 200: Search completed successfully with filtered jobs and diagnostics.
    - 500: Muse API unavailable on first fetch or unexpected internal failure.
    """
    # Gets the list of jobs from The Muse API based on the provided query parameters 
    url = "https://www.themuse.com/api/public/jobs"
    params_base = []
    normalized_keyword_query = _normalize_text(q)
    parsed_posted_after = _parse_posted_after_input(posted_after)
    posted_after_iso = parsed_posted_after.isoformat() if parsed_posted_after else ""

    if MUSE_API_KEY:
        params_base.append(("api_key", MUSE_API_KEY))
    
    # If the user provided any of the optional parameters (category, level, location, company), 
    # It adds them to the params dictionary in the format expected by The Muse API.
    categories = []
    for cat in (category or []):
        value = (cat or "").strip()
        if value:
            categories.append(value)
    for cat in (catogory or []):
        value = (cat or "").strip()
        if value:
            categories.append(value)

    # Preserve first-seen order while removing duplicates.
    categories = list(dict.fromkeys(categories))

    expanded_categories: List[str] = []
    for cat in categories:
        expanded_categories.extend(_expand_category_for_muse(cat))

    expanded_categories = [value for value in dict.fromkeys([c.strip() for c in expanded_categories if c.strip()])]

    if expanded_categories:
        for cat in expanded_categories:
            params_base.append(("category", cat))
    normalized_levels: List[str] = []
    if level:
        for lvl in level:
            normalized_level = _normalize_level_for_muse(lvl)
            if normalized_level:
                normalized_levels.append(normalized_level)
                params_base.append(("level", normalized_level))
    requested_location_count = len(location or [])
    location_param_cap = max(1, settings.MUSE_LOCATION_PARAM_CAP)
    location_params_truncated = False
    raw_location_inputs = [" ".join((loc or "").strip().split()) for loc in (location or []) if (loc or "").strip()]

    if raw_location_inputs:
        await ensure_muse_location_index()
        selected_locations, location_canonicalization = _canonicalize_selected_locations(
            raw_locations=raw_location_inputs,
            location_mode=location_mode,
            location_country_code=location_country_code,
            location_param_cap=location_param_cap,
            db=db,
        )
        location_params_truncated = location_canonicalization["requested_unique_count"] > len(selected_locations)
        for normalized_loc in selected_locations:
            params_base.append(("location", normalized_loc))
    else:
        selected_locations = []
        location_canonicalization = {
            "canonicalized_count": 0,
            "transformed_count": 0,
            "unmatched_count": 0,
            "requested_unique_count": 0,
            "dropped_count": 0,
            "dropped_locations_sample": [],
            "strategy": "none",
            "country_scope": (location_country_code or "").upper(),
        }

    normalized_companies: List[str] = []
    if company:
        for comp in company:
            normalized_comp = (comp or "").strip()
            if normalized_comp:
                normalized_companies.append(normalized_comp)
                params_base.append(("company", normalized_comp))

    cache_signature = _build_jobs_filter_signature(
        expanded_categories=expanded_categories,
        normalized_levels=normalized_levels,
        selected_locations=selected_locations,
        normalized_companies=normalized_companies,
        include_remote=include_remote,
        include_hybrid=include_hybrid,
        location_mode=(location_mode or "").strip().lower(),
        location_country_code=(location_country_code or "").strip().upper(),
        keyword_query=normalized_keyword_query,
        posted_after_iso=posted_after_iso,
        page_size=page_size,
    )
    cached_response = _get_jobs_cache_response(cache_signature, page)
    if cached_response is not None:
        return cached_response

    async def _run_scan(
        *,
        scan_params_base: List[tuple[str, str]],
        scan_selected_locations: List[str],
    ) -> dict[str, Any]:
        adaptive_extra_pages = 0
        if (
            settings.MUSE_ADAPTIVE_PAGE_CHASE_ENABLED
            and len(scan_selected_locations) >= max(1, settings.MUSE_ADAPTIVE_PAGE_CHASE_BREADTH_THRESHOLD)
        ):
            adaptive_extra_pages = max(0, settings.MUSE_ADAPTIVE_PAGE_CHASE_EXTRA_PAGES)

        max_pages = max(
            1,
            min(
                settings.MUSE_PAGE_CHASE_MAX_PAGES + adaptive_extra_pages,
                settings.MUSE_PAGE_CHASE_MAX_API_CALLS_PER_REQUEST + adaptive_extra_pages,
            ),
        )
        target_results = max(1, page_size) + 1
        min_filtered_ratio = min(max(settings.MUSE_PAGE_CHASE_MIN_FILTERED_RATIO, 0.0), 1.0)
        if adaptive_extra_pages > 0:
            min_filtered_ratio = min(
                min_filtered_ratio,
                min(max(settings.MUSE_ADAPTIVE_PAGE_CHASE_MIN_FILTERED_RATIO, 0.0), 1.0),
            )
        timeout_budget = max(1.0, settings.MUSE_PAGE_CHASE_TIMEOUT_SECONDS)

        accepted_jobs: List[dict[str, Any]] = []
        accepted_ids = set()
        filtered_out_count = 0
        accepted_by_concrete_location = 0
        accepted_by_remote_override = 0
        accepted_by_hybrid_override = 0
        accepted_by_constraint_overlap = 0
        constraint_parse_high_confidence = 0
        constraint_parse_medium_confidence = 0
        constraint_parse_low_confidence = 0
        source_pages_scanned = 0
        guardrail_stop_reason = ""
        first_payload = None
        window_size = max_pages
        window_start_page = ((page - 1) * window_size) + 1
        current_page = window_start_page
        has_more_source_pages = False
        last_seen_page_count = current_page
        start_time = time.monotonic()
        dropped_invalid_url_count = 0
        url_validation_checked_count = 0
        url_validation_cache_hit_count = 0
        url_validation_remaining_checks = max(0, int(settings.JOBS_URL_VALIDATION_MAX_CHECKS_PER_REQUEST))

        validation_client: Optional[httpx.AsyncClient] = None
        if _jobs_url_validation_enabled():
            validation_client = httpx.AsyncClient(
                timeout=max(0.2, float(settings.JOBS_URL_VALIDATION_TIMEOUT_SECONDS)),
                follow_redirects=True,
            )

        try:
            async with httpx.AsyncClient(timeout=timeout_budget) as client:
                while source_pages_scanned < max_pages:
                    params = [("page", current_page), *scan_params_base]
                    response = await client.get(url, params=params)
                    if response.status_code != 200:
                        if source_pages_scanned == 0:
                            raise HTTPException(status_code=500, detail="Failed to fetch jobs from The Muse API")
                        guardrail_stop_reason = f"muse_status_{response.status_code}"
                        break

                    payload = response.json()
                    if first_payload is None:
                        first_payload = payload

                    source_pages_scanned += 1
                    raw_jobs = payload.get("results", []) or []
                    page_filtered = 0
                    page_candidates: List[tuple[dict[str, Any], str]] = []

                    for raw_job in raw_jobs:
                        mapped = _map_muse_job(raw_job)
                        if not _job_matches_keyword(mapped, normalized_keyword_query):
                            page_filtered += 1
                            continue
                        if not _job_matches_posted_after(mapped, parsed_posted_after):
                            page_filtered += 1
                            continue

                        constraints = mapped.get("location_constraints") or {}
                        confidence = constraints.get("confidence")
                        if confidence == "high":
                            constraint_parse_high_confidence += 1
                        elif confidence == "medium":
                            constraint_parse_medium_confidence += 1
                        else:
                            constraint_parse_low_confidence += 1

                        constraint_compatible, compatibility_reason = _evaluate_local_compatibility(
                            constraints=constraints,
                            selected_locations=scan_selected_locations,
                            selected_country_code=(location_country_code or "").strip().upper(),
                        )
                        confidence_ok_for_filter = _confidence_meets_threshold(
                            constraints.get("confidence", "low"),
                            settings.CONSTRAINT_FILTER_MIN_CONFIDENCE,
                        )
                        use_constraint_compatibility = (
                            settings.CONSTRAINT_COMPATIBILITY_ENABLED
                            and confidence_ok_for_filter
                            and constraint_compatible
                        )
                        del use_constraint_compatibility
                        mapped["is_local_compatible_remote"] = False
                        mapped["local_compatibility_reason"] = ""

                        allowed, allow_reason = _is_job_allowed_by_preferences(
                            has_remote=mapped.get("has_remote", False),
                            has_hybrid=mapped.get("has_hybrid", False),
                            include_remote=include_remote,
                            include_hybrid=include_hybrid,
                            job_locations=mapped.get("all_location_names", []) or [],
                            selected_locations=scan_selected_locations,
                            allow_local_compatible_remote=False,
                        )

                        if not allowed:
                            page_filtered += 1
                            continue

                        page_candidates.append((mapped, allow_reason))

                    page_dropped_invalid = 0
                    if page_candidates and validation_client is not None and url_validation_remaining_checks > 0:
                        page_candidates, validation_stats = await _validate_candidate_job_urls(
                            page_candidates,
                            url_client=validation_client,
                            remaining_checks=url_validation_remaining_checks,
                        )
                        page_dropped_invalid = int(validation_stats.get("dropped_count") or 0)
                        dropped_invalid_url_count += page_dropped_invalid
                        url_validation_checked_count += int(validation_stats.get("checked_count") or 0)
                        url_validation_cache_hit_count += int(validation_stats.get("cache_hit_count") or 0)
                        url_validation_remaining_checks = max(
                            0,
                            url_validation_remaining_checks - int(validation_stats.get("request_count") or 0),
                        )

                    for mapped, allow_reason in page_candidates:
                        job_id = mapped.get("id")
                        if job_id in accepted_ids:
                            continue

                        accepted_ids.add(job_id)
                        accepted_jobs.append(mapped)
                        if allow_reason == "concrete_location":
                            accepted_by_concrete_location += 1
                        elif allow_reason == "remote_override":
                            accepted_by_remote_override += 1
                        elif allow_reason == "hybrid_override":
                            accepted_by_hybrid_override += 1
                    filtered_out_count += page_filtered

                    if len(accepted_jobs) >= target_results:
                        guardrail_stop_reason = "target_reached"
                        break

                    total_on_page = len(raw_jobs)
                    effective_filtered_for_guardrail = page_filtered + page_dropped_invalid
                    filtered_ratio = (effective_filtered_for_guardrail / total_on_page) if total_on_page else 0.0
                    next_page = (payload.get("page") or current_page) + 1
                    page_count = payload.get("page_count") or current_page
                    has_more_source_pages = next_page <= page_count
                    last_seen_page_count = page_count

                    if not settings.MUSE_PAGE_CHASE_ENABLED:
                        guardrail_stop_reason = "disabled"
                        break
                    if filtered_ratio < min_filtered_ratio:
                        guardrail_stop_reason = "low_filtered_ratio"
                        break
                    if next_page > page_count:
                        guardrail_stop_reason = "page_count_end"
                        break
                    if time.monotonic() - start_time >= timeout_budget:
                        guardrail_stop_reason = "timeout_budget"
                        break

                    current_page = next_page
        finally:
            if validation_client is not None:
                await validation_client.aclose()

        if first_payload is None:
            raise HTTPException(status_code=500, detail="Failed to fetch jobs from The Muse API")
        if not guardrail_stop_reason:
            guardrail_stop_reason = "max_pages_reached"

        return {
            "accepted_jobs": accepted_jobs,
            "filtered_out_count": filtered_out_count,
            "accepted_by_concrete_location": accepted_by_concrete_location,
            "accepted_by_remote_override": accepted_by_remote_override,
            "accepted_by_hybrid_override": accepted_by_hybrid_override,
            "accepted_by_constraint_overlap": accepted_by_constraint_overlap,
            "constraint_parse_high_confidence": constraint_parse_high_confidence,
            "constraint_parse_medium_confidence": constraint_parse_medium_confidence,
            "constraint_parse_low_confidence": constraint_parse_low_confidence,
            "source_pages_scanned": source_pages_scanned,
            "guardrail_stop_reason": guardrail_stop_reason,
            "first_payload": first_payload,
            "window_size": window_size,
            "window_start_page": window_start_page,
            "has_more_source_pages": has_more_source_pages,
            "source_page_count": last_seen_page_count,
            "adaptive_extra_pages": adaptive_extra_pages,
            "effective_max_pages": max_pages,
            "effective_min_filtered_ratio": min_filtered_ratio,
            "dropped_invalid_url_count": dropped_invalid_url_count,
            "url_validation_checked_count": url_validation_checked_count,
            "url_validation_cache_hit_count": url_validation_cache_hit_count,
        }

    location_relaxed_fallback = False
    effective_selected_locations = list(selected_locations)
    effective_params_base = list(params_base)
    scan_result = await _run_scan(
        scan_params_base=effective_params_base,
        scan_selected_locations=effective_selected_locations,
    )

    if _should_run_location_relaxed_fallback(
        page=page,
        accepted_jobs_count=len(scan_result["accepted_jobs"]),
        selected_locations=selected_locations,
        location_relaxed_fallback=location_relaxed_fallback,
    ):
        location_relaxed_fallback = True
        effective_selected_locations = []
        effective_params_base = _strip_location_params(params_base)
        scan_result = await _run_scan(
            scan_params_base=effective_params_base,
            scan_selected_locations=effective_selected_locations,
        )

    accepted_jobs = scan_result["accepted_jobs"]
    first_payload = scan_result["first_payload"]
    source_pages_scanned = int(scan_result["source_pages_scanned"])
    filtered_out_count = int(scan_result["filtered_out_count"])
    accepted_by_concrete_location = int(scan_result["accepted_by_concrete_location"])
    accepted_by_remote_override = int(scan_result["accepted_by_remote_override"])
    accepted_by_hybrid_override = int(scan_result["accepted_by_hybrid_override"])
    accepted_by_constraint_overlap = int(scan_result["accepted_by_constraint_overlap"])
    constraint_parse_high_confidence = int(scan_result["constraint_parse_high_confidence"])
    constraint_parse_medium_confidence = int(scan_result["constraint_parse_medium_confidence"])
    constraint_parse_low_confidence = int(scan_result["constraint_parse_low_confidence"])
    guardrail_stop_reason = scan_result["guardrail_stop_reason"]
    has_more_source_pages = bool(scan_result["has_more_source_pages"])
    last_seen_page_count = int(scan_result["source_page_count"])
    adaptive_extra_pages = int(scan_result["adaptive_extra_pages"])
    max_pages = int(scan_result["effective_max_pages"])
    min_filtered_ratio = float(scan_result["effective_min_filtered_ratio"])
    window_start_page = int(scan_result["window_start_page"])
    window_size = int(scan_result["window_size"])
    dropped_invalid_url_count = int(scan_result["dropped_invalid_url_count"])
    url_validation_checked_count = int(scan_result["url_validation_checked_count"])
    url_validation_cache_hit_count = int(scan_result["url_validation_cache_hit_count"])

    effective_location_canonicalization = dict(location_canonicalization)
    if location_relaxed_fallback:
        effective_location_canonicalization["strategy"] = (
            f"{effective_location_canonicalization.get('strategy') or 'none'}-relaxed-fallback"
        )
        effective_location_canonicalization["canonicalized_count"] = 0
        effective_location_canonicalization["dropped_count"] = 0
        effective_location_canonicalization["dropped_locations_sample"] = []
        effective_location_canonicalization["strict_state_blocked_count"] = 0
        effective_location_canonicalization["state_diversity_count"] = 0

    # Returns structured response with original pagination info and guarded-fetch diagnostics.
    page_jobs = accepted_jobs[:page_size]
    # Keep UI pagination conservative and monotonic: only advertise next page when we
    # have direct filtered evidence beyond the current page window.
    has_next_page_filtered = len(accepted_jobs) > page_size

    raw_total_jobs = int(first_payload.get("total") or 0)
    filtered_total_jobs_estimate = max(0, (page - 1) * page_size) + len(page_jobs)
    if has_next_page_filtered:
        filtered_total_jobs_estimate += 1

    if not has_next_page_filtered:
        if not page_jobs and page > 1:
            filtered_total_pages = page - 1
        else:
            filtered_total_pages = page
    else:
        filtered_total_pages = page + 1

    filter_metadata = _build_jobs_filter_metadata_payload(db)
    response_payload = {
        "page": first_payload.get("page"),
        "total_pages": filtered_total_pages,
        "total_jobs": filtered_total_jobs_estimate,
        "total_pages_estimated": filtered_total_pages,
        "total_jobs_estimated": filtered_total_jobs_estimate,
        "totals_are_estimated": True,
        "total_estimate_strategy": "lower-bound-window",
        "raw_total_pages": first_payload.get("page_count"),
        "raw_total_jobs": raw_total_jobs,
        "jobs": page_jobs,
        "source_pages_scanned": source_pages_scanned,
        "filtered_out_count": filtered_out_count,
        "guardrail_stop_reason": guardrail_stop_reason,
        "ui_page": page,
        "page_size": page_size,
        "has_next_page": has_next_page_filtered,
        "has_previous_page": page > 1,
        "requested_location_count": requested_location_count,
        "location_params_used": len(effective_selected_locations),
        "used_location_count": len(effective_selected_locations),
        "location_params_truncated": location_params_truncated,
        "dropped_location_count": int(effective_location_canonicalization.get("dropped_count") or 0),
        "dropped_locations_sample": effective_location_canonicalization.get("dropped_locations_sample") or [],
        "location_mode": (location_mode or "").strip().lower(),
        "location_country_code": (location_country_code or "").strip().upper(),
        "location_selection_strategy": effective_location_canonicalization.get("strategy"),
        "requested_locations_sample": raw_location_inputs[:12],
        "selected_locations_sample": effective_selected_locations[:12],
        "canonicalized_location_count": int(effective_location_canonicalization.get("canonicalized_count") or 0),
        "transformed_location_count": int(effective_location_canonicalization.get("transformed_count") or 0),
        "unmatched_location_count": int(effective_location_canonicalization.get("unmatched_count") or 0),
        "strict_state_blocked_count": int(effective_location_canonicalization.get("strict_state_blocked_count") or 0),
        "selected_state_diversity_count": int(effective_location_canonicalization.get("state_diversity_count") or 0),
        "accepted_by_concrete_location": accepted_by_concrete_location,
        "accepted_by_remote_override": accepted_by_remote_override,
        "accepted_by_hybrid_override": accepted_by_hybrid_override,
        "accepted_by_constraint_overlap": 0,
        "constraint_parse_high_confidence": constraint_parse_high_confidence,
        "constraint_parse_medium_confidence": constraint_parse_medium_confidence,
        "constraint_parse_low_confidence": constraint_parse_low_confidence,
        "constraint_policy_remote_off": "strict-exclude",
        "constraint_compatibility_enabled": False,
        "constraint_filter_min_confidence": "",
        "adaptive_chase_enabled": settings.MUSE_ADAPTIVE_PAGE_CHASE_ENABLED,
        "adaptive_chase_extra_pages": adaptive_extra_pages,
        "effective_max_pages": max_pages,
        "effective_min_filtered_ratio": min_filtered_ratio,
        "window_start_page": window_start_page,
        "window_size": window_size,
        "has_more_source_pages": has_more_source_pages,
        "has_next_page_possible_raw": has_more_source_pages,
        "source_page_count": last_seen_page_count,
        "dropped_invalid_url_count": dropped_invalid_url_count,
        "url_validation_checked_count": url_validation_checked_count,
        "url_validation_cache_hit_count": url_validation_cache_hit_count,
        "location_relaxed_fallback": location_relaxed_fallback,
        "keyword_query": normalized_keyword_query,
        "posted_after": posted_after_iso,
        "jobs_filter_metadata_version": filter_metadata.get("metadata_version"),
        "jobs_filter_metadata_hash": filter_metadata.get("metadata_hash"),
        "cache_hit": False,
    }
    _set_jobs_cache_response(cache_signature, page, response_payload)
    return response_payload

@router.post(
    "/jobs/save",
    tags=["jobs"],
    response_description="Confirmation payload for save operation.",
    responses={
        200: {
            "description": "Job saved successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Successfully saved Software Engineer at Acme!"
                    }
                }
            },
        },
        400: {
            "description": "Job already exists in saved list.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Job already saved"
                    }
                }
            },
        },
    },
)
async def save_job(
    job_data: SaveJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save a job posting to a user's saved-jobs list.

    Prevents duplicate saves based on provider-aware identifiers when available
    and stores a legacy snapshot for later retrieval.

    Response codes:
    - 200: Job saved successfully.
    - 400: Job already saved for this user.
    """
    normalized_provider_job_id = " ".join(str(job_data.provider_job_id or "").split())
    legacy_job_id = _normalize_saved_job_legacy_id(normalized_provider_job_id)
    existing_job = _find_existing_saved_job(
        db,
        user_id=current_user.id,
        provider=job_data.provider,
        provider_job_id=normalized_provider_job_id,
        legacy_job_id=legacy_job_id,
    )

    if existing_job:
        raise HTTPException(status_code=400, detail="Job already saved")

    new_saved_job = SavedJob(
        user_id=current_user.id,
        job_id=legacy_job_id,
        provider=job_data.provider,
        provider_job_id=normalized_provider_job_id,
        title=job_data.name,
        company=job_data.company,
        url=job_data.url
    )
    db.add(new_saved_job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_job = _find_existing_saved_job(
            db,
            user_id=current_user.id,
            provider=job_data.provider,
            provider_job_id=normalized_provider_job_id,
            legacy_job_id=legacy_job_id,
        )
        if existing_job:
            raise HTTPException(status_code=400, detail="Job already saved")
        logger.exception(
            "Saved job commit failed with integrity error for user_id=%s provider=%s provider_job_id=%s",
            current_user.id,
            job_data.provider,
            normalized_provider_job_id,
        )
        raise HTTPException(status_code=500, detail="Could not save job right now")
    except SQLAlchemyError:
        db.rollback()
        logger.exception(
            "Saved job commit failed for user_id=%s provider=%s provider_job_id=%s",
            current_user.id,
            job_data.provider,
            normalized_provider_job_id,
        )
        raise HTTPException(status_code=500, detail="Could not save job right now")
    db.refresh(new_saved_job)
    return {
        "saved_job_id": new_saved_job.id,
        "message": f"Successfully saved {job_data.name} at {job_data.company}!",
    }


@router.get(
    "/jobs/saved",
    tags=["jobs"],
    response_description="Saved jobs owned by the requested user.",
    responses={
        200: {
            "description": "Saved jobs fetched successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "saved_jobs": [
                            {
                                "id": 1,
                                "title": "Software Engineer",
                                "company": "Acme",
                                "job_url": "https://www.themuse.com/jobs/acme/software-engineer",
                            }
                        ]
                    }
                }
            },
        }
    },
)
async def get_saved_jobs(
    page: int = Query(1, ge=1, description="Saved jobs page number."),
    page_size: int = Query(10, ge=1, le=100, description="Saved jobs page size."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve all saved jobs for the authenticated user.

    Response codes:
    - 200: Saved jobs returned successfully (possibly empty list).
    """
    page = max(int(page or 1), 1)
    page_size = max(min(int(page_size or 10), 100), 1)

    saved_query = (
        db.query(SavedJob)
        .filter(SavedJob.user_id == current_user.id)
        .order_by(SavedJob.created_at.desc().nullslast(), SavedJob.id.desc())
    )
    total_jobs = int(saved_query.count() or 0)
    total_pages = max(1, ((total_jobs - 1) // page_size) + 1) if total_jobs else 1
    rows = saved_query.offset((page - 1) * page_size).limit(page_size).all()

    saved_job_data = [_serialize_saved_job_row(job, db) for job in rows]
    return {
        "saved_jobs": saved_job_data,
        "page": page,
        "page_size": page_size,
        "total_jobs": total_jobs,
        "total_pages": total_pages,
        "has_next_page": page < total_pages,
        "has_previous_page": page > 1,
    }


@router.delete("/jobs/saved/{job_id}", tags=["jobs"])
async def unsave_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    saved = db.query(SavedJob).filter(
        SavedJob.id == job_id,
        SavedJob.user_id == current_user.id
    ).first()
    if not saved:
        raise HTTPException(status_code=404, detail="Saved job not found")
    db.delete(saved)
    db.commit()
    return {"message": "Job removed from saved list"}

GOOGLE_OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _google_config_or_raise() -> tuple[str, str, str]:
    client_id = (GOOGLE_CLIENT_ID or "").strip()
    client_secret = (GOOGLE_CLIENT_SECRET or "").strip()
    redirect_uri = (GOOGLE_REDIRECT_URI or "").strip()
    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")
    return client_id, client_secret, redirect_uri


def _frontend_url(path: str, query: dict[str, str] | None = None, fragment: dict[str, str] | None = None) -> str:
    base = (settings.PUBLIC_APP_URL or "").rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    url = f"{base}{normalized_path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    if fragment:
        url = f"{url}#{urlencode(fragment)}"
    return url


def _sanitize_next_path(next_path: str | None) -> str:
    candidate = (next_path or "").strip()
    if not candidate or not candidate.startswith("/") or candidate.startswith("//"):
        return "/home"
    return candidate


def _build_google_authorization_url(state: str, redirect_uri: str, client_id: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{GOOGLE_OAUTH_URL}?{urlencode(params)}"


def _clear_google_oauth_session(request: Request) -> None:
    request.session.pop("oauth_state", None)
    request.session.pop("oauth_mode", None)
    request.session.pop("oauth_user_id", None)
    request.session.pop("oauth_next", None)
    request.session.pop("oauth_intent", None)
    request.session.pop("oauth_client", None)


def _oauth_login_error(reason: str, intent: str = "login") -> RedirectResponse:
    route = "/register" if (intent or "").strip().lower() == "register" else "/login"
    return RedirectResponse(
        _frontend_url(route, query={"oauth": "error", "provider": "google", "reason": reason})
    )


def _oauth_settings_redirect(status: str, reason: str | None = None) -> RedirectResponse:
    query = {"accounts": status, "provider": "google"}
    if reason:
        query["reason"] = reason
    return RedirectResponse(_frontend_url("/settings", query=query))


@router.get(
    "/auth/google",
    tags=["google auth"],
    response_description="Redirects browser to Google OAuth consent screen for login/registration.",
    responses={
        307: {
            "description": "Temporary redirect to Google OAuth endpoint."
        },
        302: {
            "description": "Redirect to Google OAuth endpoint (client/ASGI dependent)."
        },
    },
)
async def google_oauth(
    request: Request,
    intent: str = Query("login", description="Optional UI intent for telemetry. Supported: login, register."),
    next: str | None = Query(None, description="Optional post-login app path, e.g. /home or /job-board."),
    client: str | None = Query(None, description="Optional client hint. Use `extension` for browser-extension sign-in."),
):
    """
    Start Google OAuth flow for unauthenticated sign-in/up.

    Response codes:
    - 307/302: Redirect to Google OAuth consent screen.
    """
    client_id, _, redirect_uri = _google_config_or_raise()
    normalized_intent = (intent or "login").strip().lower()
    if normalized_intent not in {"login", "register"}:
        normalized_intent = "login"

    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    request.session["oauth_mode"] = "login"
    request.session["oauth_intent"] = normalized_intent
    request.session["oauth_next"] = _sanitize_next_path(next)
    request.session["oauth_client"] = resolve_auth_client(request, query_client=client)

    return RedirectResponse(_build_google_authorization_url(state, redirect_uri, client_id))


@router.post(
    "/auth/google/connect/start",
    tags=["google auth"],
    response_description="Returns Google OAuth authorization URL for connecting a Google account to an existing user.",
)
async def start_google_connect(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Start Google OAuth flow for linking Google to an authenticated account.
    """
    client_id, _, redirect_uri = _google_config_or_raise()
    state = secrets.token_urlsafe(16)

    request.session["oauth_state"] = state
    request.session["oauth_mode"] = "connect"
    request.session["oauth_user_id"] = int(current_user.id)
    request.session["oauth_next"] = "/settings"
    request.session["oauth_client"] = resolve_auth_client(request)

    return {"authorization_url": _build_google_authorization_url(state, redirect_uri, client_id)}


@router.get(
    "/auth/connected-accounts",
    tags=["google auth"],
    response_description="Connected account status payload for Settings.",
)
def connected_accounts(
    current_user: User = Depends(get_current_user),
):
    """
    Return connected-account state for the authenticated user.
    """
    google_connected = bool(current_user.google_id)
    has_password = bool(current_user.hashed_password)
    providers = [
        {
            "provider": "google",
            "label": "Google",
            "connected": google_connected,
            "account_email": current_user.email if google_connected else None,
            "can_connect": not google_connected,
            "can_disconnect": google_connected and has_password,
            "disconnect_disabled_reason": (
                "Set a password before disconnecting your only sign-in method."
                if google_connected and not has_password
                else None
            ),
            "coming_soon": False,
        },
        {
            "provider": "linkedin",
            "label": "LinkedIn",
            "connected": False,
            "account_email": None,
            "can_connect": False,
            "can_disconnect": False,
            "disconnect_disabled_reason": None,
            "coming_soon": True,
        },
    ]
    return {
        "providers": providers,
        "has_password": has_password,
    }


@router.delete(
    "/auth/google/disconnect",
    tags=["google auth"],
    response_description="Disconnect currently linked Google account.",
)
def disconnect_google_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Disconnect Google as a login method for the current account.
    """
    if not current_user.google_id:
        return {"message": "Google account already disconnected"}

    if not current_user.hashed_password:
        raise HTTPException(
            status_code=400,
            detail="Cannot disconnect Google without another sign-in method. Set a password first.",
        )

    current_user.google_id = None
    db.commit()
    return {"message": "Google account disconnected"}


@router.get(
    "/auth/google/callback",
    tags=["google auth"],
    response_description="Completes Google OAuth and redirects browser back to frontend.",
    responses={
        302: {
            "description": "Redirect to frontend OAuth callback/login/settings after processing."
        },
    },
)
async def google_oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code returned by Google after user consent."),
    state: str = Query(..., description="State token returned by Google; must match session value for CSRF protection."),
    db: Session = Depends(get_db),
):
    """
    Complete Google OAuth flow, then redirect to the frontend.
    """
    oauth_intent = (request.session.get("oauth_intent") or "login").strip().lower()

    try:
        client_id, client_secret, redirect_uri = _google_config_or_raise()
    except HTTPException:
        _clear_google_oauth_session(request)
        return _oauth_login_error("not_configured", intent=oauth_intent)

    expected_state = request.session.get("oauth_state")
    oauth_mode = (request.session.get("oauth_mode") or "login").strip().lower()
    oauth_user_id = request.session.get("oauth_user_id")
    oauth_next = _sanitize_next_path(request.session.get("oauth_next"))
    oauth_client = resolve_auth_client(query_client=request.session.get("oauth_client"))

    if not expected_state or state != expected_state:
        _clear_google_oauth_session(request)
        if oauth_mode == "connect":
            return _oauth_settings_redirect("error", "invalid_state")
        return _oauth_login_error("invalid_state", intent=oauth_intent)

    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token_response_data = token_response.json()
        access_token = token_response_data.get("access_token")
        if not access_token:
            _clear_google_oauth_session(request)
            if oauth_mode == "connect":
                return _oauth_settings_redirect("error", "token_exchange_failed")
            return _oauth_login_error("token_exchange_failed", intent=oauth_intent)

        profile_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if profile_response.status_code != 200:
            _clear_google_oauth_session(request)
            if oauth_mode == "connect":
                return _oauth_settings_redirect("error", "profile_fetch_failed")
            return _oauth_login_error("profile_fetch_failed", intent=oauth_intent)

        profile_data = profile_response.json()

        google_id = profile_data.get("sub")
        email = (profile_data.get("email") or "").strip().lower()
        name = profile_data.get("name")
        picture = profile_data.get("picture")
        email_verified = bool(profile_data.get("email_verified"))

    if not google_id or not email:
        _clear_google_oauth_session(request)
        if oauth_mode == "connect":
            return _oauth_settings_redirect("error", "missing_profile_fields")
        return _oauth_login_error("missing_profile_fields", intent=oauth_intent)

    if not email_verified:
        _clear_google_oauth_session(request)
        if oauth_mode == "connect":
            return _oauth_settings_redirect("error", "email_not_verified")
        return _oauth_login_error("email_not_verified", intent=oauth_intent)

    if oauth_mode == "connect":
        if not oauth_user_id:
            _clear_google_oauth_session(request)
            return _oauth_settings_redirect("error", "connect_state_missing")

        user = db.query(User).filter(User.id == int(oauth_user_id)).first()
        if not user:
            _clear_google_oauth_session(request)
            return _oauth_settings_redirect("error", "user_not_found")

        google_owner = db.query(User).filter(User.google_id == google_id).first()
        if google_owner and google_owner.id != user.id:
            _clear_google_oauth_session(request)
            return _oauth_settings_redirect("error", "google_already_linked")

        email_owner = db.query(User).filter(func.lower(User.email) == email).first()
        if email_owner and email_owner.id != user.id:
            _clear_google_oauth_session(request)
            return _oauth_settings_redirect("error", "email_conflict")

        user.google_id = google_id
        user.username = (user.email or "").strip().lower()
        if picture:
            user.picture_url = picture
        if name and not user.full_name:
            user.full_name = name
        if email_verified and user.email and user.email.lower() == email:
            user.email_verified = True
        db.commit()

        _clear_google_oauth_session(request)
        return _oauth_settings_redirect("connected")

    try:
        user = GoogleAuthService.get_or_create_user(
            db=db,
            google_id=google_id,
            email=email,
            full_name=name,
            picture_url=picture,
            email_verified=email_verified,
        )
    except ValueError as exc:
        _clear_google_oauth_session(request)
        return _oauth_login_error(str(exc).strip() or "account_link_not_allowed", intent=oauth_intent)

    if not user.is_active:
        _clear_google_oauth_session(request)
        return _oauth_login_error("account_inactive", intent=oauth_intent)

    user_access_token = create_access_token_for_client(data={"sub": str(user.id)}, client=oauth_client)
    redirect_url = _frontend_url(
        "/oauth-callback",
        query={
            "next": oauth_next,
            "provider": "google",
        },
    )
    redirect_response = RedirectResponse(redirect_url, status_code=302)
    set_auth_cookie(
        redirect_response,
        user_access_token,
        max_age=access_token_expire_seconds_for_client(oauth_client),
    )
    _clear_google_oauth_session(request)
    return redirect_response


@router.get(
    "/status",
    tags=["status"],
    response_description="Lightweight backend status payload.",
    responses={
        200: {
            "description": "Backend status returned.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "environment": "dev",
                        "message": "UAH API is running",
                    }
                }
            },
        }
    },
)
async def api_status():
    """
    Lightweight status endpoint for frontend connectivity checks.

    Returns a minimal service health payload used by the frontend to confirm
    `/api` proxy routing and basic backend availability.

    Response codes:
    - 200: Service is reachable.
    """
    return {
        "status": "ok",
        "environment": "dev",
        "message": "UAH API is running",
    }


@router.get(
    "/diagnostics",
    tags=["status"],
    response_description="Comprehensive multi-service diagnostics snapshot.",
    responses={
        200: {
            "description": "Diagnostics payload returned.",
            "content": {
                "application/json": {
                    "example": {
                        "timestamp": "2026-03-31T22:12:10.421Z",
                        "environment": "dev",
                        "services": {
                            "backend": {"status": "healthy", "name": "UAH", "version": "0.1.0"},
                            "database": {"status": "healthy", "latency_ms": 5.2},
                        },
                    }
                }
            },
        },
        500: {
            "description": "One or more diagnostics probes failed unexpectedly."
        },
    },
)
async def diagnostics(
    current_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
):
    """
    Comprehensive diagnostics endpoint for operational visibility.

    Probes backend runtime metadata, database connectivity, and selected
    integration checks, returning a deep status object used by troubleshooting
    tools and status dashboards.

    Response codes:
    - 200: Diagnostics gathered successfully.
    - 500: One or more probes failed unexpectedly.
    """
    import time
    import platform
    import sys
    import os
    from datetime import datetime, timezone

    from app.core.config import settings

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": os.getenv("ENV", "dev"),
        "services": {},
    }

    method_availability = await get_pipeline_availability()
    parse_method_statuses = []
    parse_method_messages = {
        "cloud": "Cloud AI parsing is available.",
        "local": "Local AI parsing is available.",
        "rules": "Deterministic rules parsing is available.",
    }

    # --- Backend info ---
    result["services"]["backend"] = {
        "status": "healthy",
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "python_version": sys.version,
        "platform": platform.platform(),
        "pid": os.getpid(),
        "framework": f"FastAPI (uvicorn)",
        "host": os.getenv("HOSTNAME", "unknown"),
    }

    # --- Database probe ---
    db_start = time.monotonic()
    try:
        from sqlalchemy import text
        from app.db.session import get_engine

        engine = get_engine()

        with engine.connect() as conn:
            row = conn.execute(text("SELECT version()")).fetchone()
            pg_version = row[0] if row else "unknown"

            row = conn.execute(text("SELECT current_database()")).fetchone()
            db_name = row[0] if row else "unknown"

            row = conn.execute(text("SELECT current_user")).fetchone()
            db_user = row[0] if row else "unknown"

            row = conn.execute(text(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            )).fetchone()
            db_size = row[0] if row else "unknown"

            row = conn.execute(text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )).fetchone()
            table_count = row[0] if row else 0

        db_latency = round((time.monotonic() - db_start) * 1000, 2)

        result["services"]["database"] = {
            "status": "healthy",
            "latency_ms": db_latency,
            "postgres_version": pg_version,
            "database_name": db_name,
            "user": db_user,
            "size": db_size,
            "public_tables": table_count,
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
        }
    except Exception as e:
        db_latency = round((time.monotonic() - db_start) * 1000, 2)
        result["services"]["database"] = {
            "status": "unhealthy",
            "latency_ms": db_latency,
            "error": str(e),
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
        }

    # --- Network / DNS probe (can backend resolve service names?) ---
    import socket

    # On the live dev server, "backend" resolves to the Docker container IP.
    # Locally (running on host), "backend" won't resolve, which is expected.
    # To prevent local tests from showing "degraded", we conditionally check
    # the hostname if we're not inside Docker or if POSTGRES_HOST is localhost.
    dns_checks = {"db": settings.POSTGRES_HOST}
    if settings.POSTGRES_HOST != "localhost":
        dns_checks["backend"] = "backend"

    network_results = {}
    for name, host in dns_checks.items():
        try:
            ip = socket.gethostbyname(host)
            network_results[name] = {"resolved": True, "ip": ip}
        except socket.gaierror:
            network_results[name] = {"resolved": False, "ip": None}

    result["services"]["network"] = {
        "status": "healthy" if all(r["resolved"] for r in network_results.values()) else "degraded",
        "dns_resolution": network_results,
    }

    parse_method_entries = {}
    for method_key in ("cloud", "local", "rules"):
        method_info = method_availability.get(method_key) or {}
        method_available = bool(method_info.get("available"))
        method_status = "healthy" if method_available else "degraded"
        parse_method_statuses.append(method_status)
        parse_method_entries[method_key] = {
            "available": method_available,
            "status": method_status,
            "message": method_info.get("message") or parse_method_messages[method_key],
        }

    result["services"]["parse_methods"] = {
        "status": "healthy" if all(status == "healthy" for status in parse_method_statuses) else "degraded",
        "methods": parse_method_entries,
    }

    # --- Job board diagnostics (compact) ---
    try:
        from app.api import jobs as jobs_api
        from app.services.job_board_debug import build_compact_job_board_service_status
        from app.services.job_search import search_local_jobs

        filter_started = time.monotonic()
        filter_metadata = _build_jobs_filter_metadata_payload(db)
        filter_latency_ms = round((time.monotonic() - filter_started) * 1000, 2)

        providers_started = time.monotonic()
        provider_payload = jobs_api.list_job_provider_attribution()
        providers_latency_ms = round((time.monotonic() - providers_started) * 1000, 2)

        local_search_started = time.monotonic()
        local_search_payload = search_local_jobs(db=db, page=1, page_size=1)
        local_search_latency_ms = round((time.monotonic() - local_search_started) * 1000, 2)

        compact_status = build_compact_job_board_service_status(db)
        result["services"]["job_board"] = {
            **compact_status,
            "endpoints": {
                "/api/jobs/filter-metadata": {
                    "status": "healthy",
                    "latency_ms": filter_latency_ms,
                    "metadata_version": filter_metadata.get("metadata_version"),
                },
                "/api/providers/attribution": {
                    "status": "healthy",
                    "latency_ms": providers_latency_ms,
                    "provider_count": len(provider_payload.get("providers") or []),
                },
                "/api/jobs/search": {
                    "status": "healthy",
                    "latency_ms": local_search_latency_ms,
                    "sample_total_jobs": int(local_search_payload.get("total_jobs") or 0),
                },
            },
        }
    except Exception as e:
        result["services"]["job_board"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # --- Overall status ---
    statuses = [s.get("status") for s in result["services"].values()]
    if all(s == "healthy" for s in statuses):
        result["overall"] = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        result["overall"] = "unhealthy"
    else:
        result["overall"] = "degraded"

    return result
