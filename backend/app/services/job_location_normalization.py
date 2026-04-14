from __future__ import annotations

import re
from functools import lru_cache

from app.services.geolocation import load_city_dataset
from app.services.muse_location_index import COUNTRY_CODE_TO_NAME, COUNTRY_NAME_TO_CODE, US_STATE_CODES

_REMOTE_LIKE_RE = re.compile(
    r"\b(remote|hybrid|work\s*from\s*home|anywhere|flexible|worldwide)\b",
    re.IGNORECASE,
)
_WASHINGTON_DC_RE = re.compile(
    r"\b(washington(?:\s*,)?\s*dc|district\s+of\s+columbia)\b",
    re.IGNORECASE,
)
_US_SUBREGION_HINT_RE = re.compile(r"\b(county|borough|parish|district|metro|metropolitan)\b", re.IGNORECASE)
_AMBIGUOUS_COUNTRY_CODE_TOKENS = {"CA", "DE", "GA", "IN", "ME", "OR"}
_DOMINANT_CITY_POPULATION_MIN = 250_000
_DOMINANT_CITY_POPULATION_RATIO = 5.0
_US_STATE_NAME_TO_CODE = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}


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
def _city_records_by_name() -> dict[str, list[dict[str, str | int]]]:
    lookup: dict[str, list[dict[str, str | int]]] = {}
    try:
        cities = load_city_dataset()
    except Exception:
        cities = []

    for city in cities:
        country_code = _normalize_text(city.get("country_code")).upper()
        city_name = _normalize_key(city.get("name"))
        admin1 = _normalize_text(city.get("admin1")).upper()
        population = int(city.get("population") or 0)
        if not country_code or not city_name:
            continue

        lookup.setdefault(city_name, []).append(
            {
                "country_code": country_code,
                "admin1": admin1,
                "population": population,
            }
        )

    return lookup


def _normalize_population(value: object) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _explicit_country_from_piece(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None

    upper = normalized.upper()
    if len(upper) == 2:
        if upper in US_STATE_CODES or upper in _AMBIGUOUS_COUNTRY_CODE_TOKENS:
            return None
        if upper in COUNTRY_CODE_TO_NAME:
            return upper
        return None

    return COUNTRY_NAME_TO_CODE.get(normalized.lower())


def _us_state_code_from_piece(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None

    upper = normalized.upper()
    if upper in US_STATE_CODES:
        return upper

    return _US_STATE_NAME_TO_CODE.get(normalized.lower())


def _dominant_country_from_records(records: list[dict[str, str | int]]) -> str | None:
    if not records:
        return None

    sorted_records = sorted(
        records,
        key=lambda item: (
            -_normalize_population(item.get("population")),
            str(item.get("country_code") or ""),
            str(item.get("admin1") or ""),
        ),
    )
    if len(sorted_records) == 1:
        return str(sorted_records[0].get("country_code") or "") or None

    top_population = _normalize_population(sorted_records[0].get("population"))
    second_population = _normalize_population(sorted_records[1].get("population"))
    if top_population < _DOMINANT_CITY_POPULATION_MIN:
        return None
    if second_population <= 0:
        return str(sorted_records[0].get("country_code") or "") or None
    if top_population < int(second_population * _DOMINANT_CITY_POPULATION_RATIO):
        return None
    return str(sorted_records[0].get("country_code") or "") or None


def _infer_country_from_city_dataset(location: str) -> str | None:
    pieces = [piece.strip() for piece in _normalize_text(location).split(",") if piece.strip()]
    if not pieces:
        return None

    city_key = _normalize_key(pieces[0])
    if not city_key:
        return None

    records = list(_city_records_by_name().get(city_key) or [])
    if not records:
        return None

    admin_key = _normalize_text(pieces[1]).upper() if len(pieces) >= 2 else ""
    if admin_key:
        matching_admin_records = [item for item in records if str(item.get("admin1") or "").upper() == admin_key]
        if matching_admin_records:
            codes = {str(item.get("country_code") or "").upper() for item in matching_admin_records if item.get("country_code")}
            if len(codes) == 1:
                return next(iter(codes))
            dominant = _dominant_country_from_records(matching_admin_records)
            if dominant:
                return dominant

    return _dominant_country_from_records(records)


def _infer_us_country_from_subregion_pair(pieces: list[str]) -> str | None:
    if len(pieces) != 2:
        return None

    city_piece = _normalize_text(pieces[0])
    subregion_piece = _normalize_text(pieces[1])
    if not city_piece or not subregion_piece:
        return None
    if _explicit_country_from_piece(subregion_piece):
        return None
    if _us_state_code_from_piece(subregion_piece):
        return "US"

    inferred = _infer_country_from_city_dataset(city_piece)
    if inferred != "US":
        return None
    if _US_SUBREGION_HINT_RE.search(subregion_piece):
        return "US"

    # Arbeitnow often emits US locations as "City, Neighborhood".
    return "US"


def normalize_job_location_country(location: str | None) -> tuple[str | None, str | None]:
    normalized = _normalize_text(location)
    if not normalized:
        return (None, None)

    if _REMOTE_LIKE_RE.search(normalized):
        return (None, None)

    if _WASHINGTON_DC_RE.search(normalized):
        return ("US", _country_name_from_code("US"))

    pieces = [piece.strip() for piece in normalized.split(",") if piece.strip()]
    lowered = normalized.lower()

    for raw_piece in reversed(pieces):
        country_code = _explicit_country_from_piece(raw_piece)
        if country_code:
            return (country_code, _country_name_from_code(country_code))

    for raw_piece in reversed(pieces):
        if _us_state_code_from_piece(raw_piece):
            return ("US", _country_name_from_code("US"))

    for country_name, country_code in COUNTRY_NAME_TO_CODE.items():
        if re.search(rf"\b{re.escape(country_name)}\b", lowered):
            return (country_code, _country_name_from_code(country_code))

    inferred_us = _infer_us_country_from_subregion_pair(pieces)
    if inferred_us:
        return (inferred_us, _country_name_from_code(inferred_us))

    inferred = _infer_country_from_city_dataset(normalized)
    if inferred:
        return (inferred, _country_name_from_code(inferred))

    return (None, None)
