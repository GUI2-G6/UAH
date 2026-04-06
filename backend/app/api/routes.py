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
from contextvars import Token
import hashlib
import ipaddress
import json
import os, secrets, httpx
import httpx
import re
import time
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.models.user import User, SavedJob
from app.db.session import get_db
from app.google.service import GoogleAuthService
from app.schemas.user import TokenResponse, UserResponse, SaveJobRequest
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
from app.services.muse_location_index import (
    ensure_muse_location_index,
    list_supported_countries,
    list_supported_locations_for_country,
    refresh_muse_location_index,
)
from app.core.config import settings
from app.models.muse_location import MuseSupportedLocation


router = APIRouter()
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

_JOBS_CACHE: dict[str, dict[str, Any]] = {}

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
        return selected, {
            "canonicalized_count": len(selected),
            "transformed_count": 0,
            "unmatched_count": len(selected),
            "requested_unique_count": len(normalized_raw),
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

    return selected_locations, {
        "canonicalized_count": len(selected_locations),
        "transformed_count": transformed_count,
        "unmatched_count": unmatched_count,
        "strict_state_blocked_count": strict_state_blocked_count,
        "state_diversity_count": len({(_extract_state_code(name) or "") for name in selected_locations if _extract_state_code(name)}),
        "requested_unique_count": len(normalized_raw),
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
        elif allow_local_compatible_remote and has_remote:
            reason = "constraint_overlap"
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
        "name": job.get("name"),
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
    "/jobs/search",
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
        le=20,
        description="Number of jobs to return for the requested UI page. Max 20.",
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
    include_remote: bool = Query(False, description="When true, include fully remote roles that pass compatibility rules."),
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
        page_size=page_size,
    )
    cached_response = _get_jobs_cache_response(cache_signature, page)
    if cached_response is not None:
        return cached_response

    adaptive_extra_pages = 0
    if (
        settings.MUSE_ADAPTIVE_PAGE_CHASE_ENABLED
        and len(selected_locations) >= max(1, settings.MUSE_ADAPTIVE_PAGE_CHASE_BREADTH_THRESHOLD)
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

    accepted_jobs = []
    accepted_ids = set()
    raw_jobs_seen = 0
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

    async with httpx.AsyncClient(timeout=timeout_budget) as client:
        while source_pages_scanned < max_pages:
            params = [("page", current_page), *params_base]
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
            raw_jobs_seen += len(raw_jobs)
            page_filtered = 0

            for raw_job in raw_jobs:
                mapped = _map_muse_job(raw_job)
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
                    selected_locations=selected_locations,
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
                mapped["is_local_compatible_remote"] = constraint_compatible
                mapped["local_compatibility_reason"] = compatibility_reason

                allowed, allow_reason = _is_job_allowed_by_preferences(
                    has_remote=mapped.get("has_remote", False),
                    has_hybrid=mapped.get("has_hybrid", False),
                    include_remote=include_remote,
                    include_hybrid=include_hybrid,
                    job_locations=mapped.get("all_location_names", []) or [],
                    selected_locations=selected_locations,
                    allow_local_compatible_remote=(not include_remote and use_constraint_compatibility),
                )

                if not allowed:
                    page_filtered += 1
                    continue

                if allow_reason == "concrete_location":
                    accepted_by_concrete_location += 1
                elif allow_reason == "remote_override":
                    accepted_by_remote_override += 1
                elif allow_reason == "hybrid_override":
                    accepted_by_hybrid_override += 1
                elif allow_reason == "constraint_overlap":
                    accepted_by_constraint_overlap += 1

                job_id = mapped.get("id")
                if job_id in accepted_ids:
                    continue

                accepted_ids.add(job_id)
                accepted_jobs.append(mapped)

            filtered_out_count += page_filtered

            if len(accepted_jobs) >= target_results:
                guardrail_stop_reason = "target_reached"
                break

            total_on_page = len(raw_jobs)
            filtered_ratio = (page_filtered / total_on_page) if total_on_page else 0.0
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

    if first_payload is None:
        raise HTTPException(status_code=500, detail="Failed to fetch jobs from The Muse API")

    if not guardrail_stop_reason:
        guardrail_stop_reason = "max_pages_reached"

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
        "location_params_used": len(selected_locations),
        "used_location_count": len(selected_locations),
        "location_params_truncated": location_params_truncated,
        "location_mode": (location_mode or "").strip().lower(),
        "location_country_code": (location_country_code or "").strip().upper(),
        "location_selection_strategy": location_canonicalization.get("strategy"),
        "requested_locations_sample": raw_location_inputs[:12],
        "selected_locations_sample": selected_locations[:12],
        "canonicalized_location_count": int(location_canonicalization.get("canonicalized_count") or 0),
        "transformed_location_count": int(location_canonicalization.get("transformed_count") or 0),
        "unmatched_location_count": int(location_canonicalization.get("unmatched_count") or 0),
        "strict_state_blocked_count": int(location_canonicalization.get("strict_state_blocked_count") or 0),
        "selected_state_diversity_count": int(location_canonicalization.get("state_diversity_count") or 0),
        "accepted_by_concrete_location": accepted_by_concrete_location,
        "accepted_by_remote_override": accepted_by_remote_override,
        "accepted_by_hybrid_override": accepted_by_hybrid_override,
        "accepted_by_constraint_overlap": accepted_by_constraint_overlap,
        "constraint_parse_high_confidence": constraint_parse_high_confidence,
        "constraint_parse_medium_confidence": constraint_parse_medium_confidence,
        "constraint_parse_low_confidence": constraint_parse_low_confidence,
        "constraint_policy_remote_off": "allow-if-overlap",
        "constraint_compatibility_enabled": settings.CONSTRAINT_COMPATIBILITY_ENABLED,
        "constraint_filter_min_confidence": settings.CONSTRAINT_FILTER_MIN_CONFIDENCE,
        "adaptive_chase_enabled": settings.MUSE_ADAPTIVE_PAGE_CHASE_ENABLED,
        "adaptive_chase_extra_pages": adaptive_extra_pages,
        "effective_max_pages": max_pages,
        "effective_min_filtered_ratio": min_filtered_ratio,
        "window_start_page": window_start_page,
        "window_size": window_size,
        "has_more_source_pages": has_more_source_pages,
        "has_next_page_possible_raw": has_more_source_pages,
        "source_page_count": last_seen_page_count,
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
    # Creates an endpoint for saving a job to the user's profile with the required job data and a database session dependency.
    job_data: SaveJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save a job posting to a user's saved-jobs list.

    Prevents duplicate saves based on `(user_id, job_id)` and stores job title,
    company, and source URL for later retrieval.

    Response codes:
    - 200: Job saved successfully.
    - 400: Job already saved for this user.
    """
    # Checks if the job is already saved for the user by querying the SavedJob table in the database with the user ID and job ID.
    existing_job = db.query(SavedJob).filter(
        SavedJob.user_id == current_user.id,
        SavedJob.job_id == job_data.job_id
    ).first()
    
    # If the job is already saved, it raises an HTTP 400 error indicating that the job has already been saved by the user.
    if existing_job:
        raise HTTPException(status_code=400, detail="Job already saved")
    
    # If the job isnt saved, it creates a new SavedJob instance with the provided job data and adds it to the database session.
    new_saved_job = SavedJob(
        user_id=current_user.id,
        job_id=job_data.job_id,
        title=job_data.name,
        company=job_data.company,
        url=job_data.url
    )
    # Commits the transaction to save the new job to the database and refreshes the instance to get the updated data.
    db.add(new_saved_job)
    db.commit()
    db.refresh(new_saved_job)
    # Tells the frontend that the job has been successfully saved to the user's profile with a success message.
    return {"message": f"Successfully saved  {job_data.name} at {job_data.company}!"}


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
    user_id: int = Query(..., ge=1, description="User ID whose saved jobs should be returned."),
    db: Session = Depends(get_db),
):
    """
    Retrieve all saved jobs for a specific user.

    Returns a compact list of saved job records containing title, company, and
    destination URL fields.

    Response codes:
    - 200: Saved jobs returned successfully (possibly empty list).
    """
    # Queries the SavedJob table in the database to get all saved jobs for the specified user ID.
    saved_jobs = db.query(SavedJob).filter(SavedJob.user_id == user_id).all()
    
    # Constructs a list of saved job data with relevant information such as job ID, title, company, and job URL.
    saved_job_data = []
    for job in saved_jobs:
        saved_job_data.append({
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "job_url": job.url,
        })
    # Returns the structured JSON response containing the list of saved jobs for the user.
    return {"saved_jobs": saved_job_data}

@router.get(
    "/auth/google",
    tags=["google auth"],
    response_description="Redirects browser to Google OAuth consent screen.",
    responses={
        307: {
            "description": "Temporary redirect to Google OAuth endpoint."
        },
        302: {
            "description": "Redirect to Google OAuth endpoint (client/ASGI dependent)."
        },
    },
)
async def google_oauth(request: Request):
    """
    Start Google OAuth authorization flow.

    Creates a CSRF-protection state value, stores it in session, and redirects
    the browser to Google's OAuth consent page.

    Response codes:
    - 307/302: Redirect to Google OAuth consent screen.
    """
    # Generates a random  16 character state string to prevent attacks
    state = secrets.token_urlsafe(16)
    # Stores the state in the session for later verification when the user is redirected back
    request.session["oauth_state"] = state
    
    # Holds all the parameters required for the Google OAuth including client ID, redirect URI, response type, scope, and the generated state
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
                                
    # Creates a query string from the parameters and redirects the user to Google's OAuth 2.0 authorization endpoint with the query string attached
    query = "&".join([f"{key}={value}" for key, value in params.items()])
    # Then sends the user's browser to the Google OAuth consent screen s they can log in and authorize the application to access their Google account information. 
    # After the user completes the authorization process, Google will redirect them back to the specified redirect URI with an authorization code 
    #                                                                                                   that can be exchanged for an access token.
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")
    
    
    
@router.get(
    "/auth/google/callback",
    response_model=TokenResponse,
    tags=["google auth"],
    response_description="UAH token payload for authenticated Google user.",
    responses={
        200: {
            "description": "Google OAuth completed and local token issued.",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example.signature",
                        "token_type": "bearer",
                        "user": {
                            "id": 42,
                            "email": "jane.doe@example.com",
                            "username": "jane_doe",
                            "first_name": "Jane",
                            "last_name": "Doe",
                            "avatar_url": "https://lh3.googleusercontent.com/a-/example",
                            "email_verified": True,
                            "is_active": True,
                        },
                    }
                }
            },
        },
        400: {
            "description": "OAuth state mismatch or token exchange failure.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Invalid state parameter"
                    }
                }
            },
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
    Complete Google OAuth flow and issue local API token.

    Validates the state token, exchanges authorization code for Google tokens,
    fetches user profile claims, creates/loads the local user, and returns a
    UAH bearer token.

    Response codes:
    - 200: OAuth login completed and local token returned.
    - 400: Invalid state token or failed Google token exchange.
    """
    # Verifies if the parameter "state" matches the one stored in the session to prevent any attacks. 
    # If they don't match, it raises an HTTP 400 error.
    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state parameter")    
    
    # Opens an asynchronous HTTP client session using httpx to exchange the authorization code for an access token 
    # by making a POST request to Google's token endpoint.
    async with httpx.AsyncClient() as client:
        
        # Sends a POST request to Google's token endpoint with the required parameters including the authorization code, client ID, client secret, 
        # redirect URI, and grant type.
        token_response = await client.post("https://oauth2.googleapis.com/token", 
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        # Converts the response to JSON and extracts the access token from the response data. 
        # The access token can then be used to make authenticated requests to Google's APIs on behalf of the user.
        token_response_data = token_response.json()
        access_token = token_response_data.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to obtain access token")
        
        # Gets the user's profile information by making a GET request to Google's userinfo endpoint with the access token included in the Authorization header.
        profile_response = await client.get("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {access_token}"})
        profile_data = profile_response.json()
        
        # Extracts the user's Google ID, email, name, and profile picture URL from the profile data returned by Google.
        google_id = profile_data['sub']
        email = profile_data["email"]
        name = profile_data["name"]
        picture = profile_data.get("picture")

        
        user = GoogleAuthService.get_or_create_user(db=db, google_id=google_id, email=email, full_name=name, picture_url=picture)

        from app.core.security import create_access_token
        user_access_token = create_access_token(data={"sub": str(user.id)})
        
        return TokenResponse(access_token=user_access_token, user=UserResponse.model_validate(user),
    )


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
async def diagnostics(current_user: User = Depends(require_admin_user)):
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

    # --- Overall status ---
    statuses = [s.get("status") for s in result["services"].values()]
    if all(s == "healthy" for s in statuses):
        result["overall"] = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        result["overall"] = "unhealthy"
    else:
        result["overall"] = "degraded"

    return result
