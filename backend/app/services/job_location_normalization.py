from __future__ import annotations

import re
from functools import lru_cache

from app.services.geolocation import load_city_dataset
from app.services.muse_location_index import COUNTRY_CODE_TO_NAME, COUNTRY_NAME_TO_CODE, US_STATE_CODES

_REMOTE_LIKE_RE = re.compile(r"\b(remote|hybrid|work\s*from\s*home|anywhere|flexible)\b", re.IGNORECASE)


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _normalize_key(value: str | None) -> str:
    return _normalize_text(value).lower()


def _country_name_from_code(code: str | None) -> str | None:
    normalized = _normalize_text(code).upper()
    if not normalized:
        return None
    return COUNTRY_CODE_TO_NAME.get(normalized, normalized)


def normalize_country_code(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None

    upper = normalized.upper()
    if upper in COUNTRY_CODE_TO_NAME:
        return upper

    return COUNTRY_NAME_TO_CODE.get(normalized.lower())


def normalize_country_name(value: str | None) -> str | None:
    code = normalize_country_code(value)
    if not code:
        return None
    return _country_name_from_code(code)


@lru_cache(maxsize=1)
def _city_country_lookup() -> dict[tuple[str, str], set[str]]:
    lookup: dict[tuple[str, str], set[str]] = {}
    try:
        cities = load_city_dataset()
    except Exception:
        cities = []

    for city in cities:
        country_code = _normalize_text(city.get("country_code")).upper()
        city_name = _normalize_key(city.get("name"))
        admin1 = _normalize_text(city.get("admin1")).upper()
        if not country_code or not city_name:
            continue

        keys = {(city_name, admin1), (city_name, "")}
        for key in keys:
            lookup.setdefault(key, set()).add(country_code)

    return lookup


def _infer_country_from_city_dataset(location: str) -> str | None:
    pieces = [piece.strip() for piece in _normalize_text(location).split(",") if piece.strip()]
    if not pieces:
        return None

    city_key = _normalize_key(pieces[0])
    admin_key = _normalize_text(pieces[1]).upper() if len(pieces) >= 2 else ""
    lookup = _city_country_lookup()

    for key in ((city_key, admin_key), (city_key, "")):
        matches = lookup.get(key) or set()
        if len(matches) == 1:
            return next(iter(matches))

    return None


def normalize_job_location_country(location: str | None) -> tuple[str | None, str | None]:
    normalized = _normalize_text(location)
    if not normalized:
        return (None, None)

    pieces = [piece.strip() for piece in normalized.split(",") if piece.strip()]
    lowered = normalized.lower()

    for raw_piece in reversed(pieces):
        country_code = normalize_country_code(raw_piece)
        if country_code:
            return (country_code, _country_name_from_code(country_code))

        upper_piece = raw_piece.upper()
        if len(upper_piece) == 2 and upper_piece in US_STATE_CODES:
            return ("US", _country_name_from_code("US"))

    for country_name, country_code in COUNTRY_NAME_TO_CODE.items():
        if re.search(rf"\b{re.escape(country_name)}\b", lowered):
            return (country_code, _country_name_from_code(country_code))

    if pieces:
        trailing = pieces[-1].upper()
        if len(trailing) == 2 and trailing in US_STATE_CODES:
            return ("US", _country_name_from_code("US"))

    inferred = _infer_country_from_city_dataset(normalized)
    if inferred:
        return (inferred, _country_name_from_code(inferred))

    if _REMOTE_LIKE_RE.search(normalized):
        return (None, None)

    return (None, None)
