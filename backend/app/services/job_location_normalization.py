from __future__ import annotations

import re
from functools import lru_cache

from app.services.geolocation import load_city_dataset
from app.services.location_country_reference import (
    AU_STATE_CODES,
    CA_PROVINCE_CODES,
    COUNTRY_CLUE_PATTERNS,
    COUNTRY_CODE_TO_NAME,
    COUNTRY_NAME_TO_CODE,
    COUNTRY_TLD_TO_CODE,
    POSTAL_PATTERNS,
    PROVIDER_COUNTRY_PRIORS,
    REAL_COUNTRY_CODES,
    SPECIAL_LOCALITY_TO_COUNTRY,
    US_STATE_CODES,
    country_name_from_code,
    is_real_country_code,
    normalize_country_name_key,
    region_country_from_piece,
    searchable_country_phrases,
)

_WASHINGTON_DC_RE = re.compile(
    r"\b(washington(?:\s*,)?\s*dc|district\s+of\s+columbia)\b",
    re.IGNORECASE,
)
_SUBREGION_HINT_RE = re.compile(
    r"\b(county|borough|parish|district|metro|metropolitan|province|prefecture|oblast)\b",
    re.IGNORECASE,
)
_DIRECTIONAL_PREFIX_RE = re.compile(r"^(north|south|east|west|central|greater|metro|downtown|uptown|midtown)\s+", re.IGNORECASE)
_AMBIGUOUS_COUNTRY_CODE_TOKENS = {"CA", "DE", "GA", "IN", "ME", "OR", "SA", "WA", "NT"}
_DOMINANT_CITY_POPULATION_MIN = 250_000
_DOMINANT_CITY_POPULATION_RATIO = 5.0
_US_SUBREGION_COUNTRIES = {"US"}
_COUNTRY_CONTEXT_PHRASES = {
    "AU": ("australia", "australian"),
    "DE": ("germany", "deutschland", "german"),
    "GB": ("united kingdom", "uk", "britain", "great britain", "england", "scotland", "wales"),
    "US": ("united states", "usa", "u.s.", "u.s.a.", "american"),
}
_SENTINEL_REMOTE_GLOBAL = "XX"
_SENTINEL_UNCERTAIN = "XU"


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _normalize_key(value: str | None) -> str:
    return _normalize_text(value).lower()


def _country_name_from_code(code: str | None) -> str | None:
    normalized = _normalize_text(code).upper()
    if not normalized:
        return None
    return country_name_from_code(normalized) or COUNTRY_CODE_TO_NAME.get(normalized, normalized)


def _sentinel_country(code: str) -> tuple[str, str]:
    return (code, _country_name_from_code(code) or code)


def normalize_country_code(value: str | None) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None

    upper = normalized.upper()
    if upper in COUNTRY_CODE_TO_NAME:
        return upper

    return COUNTRY_NAME_TO_CODE.get(normalize_country_name_key(normalized))


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


def _split_location_pieces(location: str) -> list[str]:
    return [piece.strip() for piece in _normalize_text(location).split(",") if piece.strip()]


def _piece_variants(value: str | None) -> list[str]:
    normalized = _normalize_text(value)
    if not normalized:
        return []

    variants = [normalized]
    stripped_prefix = _DIRECTIONAL_PREFIX_RE.sub("", normalized)
    if stripped_prefix and stripped_prefix != normalized:
        variants.append(stripped_prefix)

    if len(normalized.split()) > 1:
        variants.append(normalized.split()[-1])

    deduped: list[str] = []
    seen: set[str] = set()
    for variant in variants:
        clean = _normalize_text(variant)
        key = clean.lower()
        if not clean or key in seen:
            continue
        seen.add(key)
        deduped.append(clean)
    return deduped


def _is_location_agnostic(location: str) -> bool:
    lowered = _normalize_key(location)
    if not lowered:
        return True

    normalized = re.sub(r"[\-/,|]+", " ", lowered)
    normalized = " ".join(normalized.split())
    if normalized in {"remote", "hybrid", "worldwide", "global", "anywhere", "flexible", "wfh", "work from home"}:
        return True

    tokens = normalized.split()
    if not tokens:
        return True
    return all(token in {"remote", "hybrid", "worldwide", "global", "anywhere", "flexible", "work", "from", "home", "wfh", "friendly"} for token in tokens)


def _explicit_country_phrase_from_text(value: str | None) -> str | None:
    key = normalize_country_name_key(value)
    if not key:
        return None

    for phrase, country_code in searchable_country_phrases():
        if re.search(rf"(?:^| ){re.escape(phrase)}(?: |$)", key):
            return country_code
    return None


def _explicit_country_from_piece(value: str | None, *, allow_ambiguous_codes: bool = False) -> str | None:
    normalized = _normalize_text(value)
    if not normalized:
        return None

    upper = normalized.upper()
    if len(upper) == 2:
        alias_code = COUNTRY_NAME_TO_CODE.get(normalize_country_name_key(normalized))
        if alias_code:
            if alias_code in _AMBIGUOUS_COUNTRY_CODE_TOKENS and not allow_ambiguous_codes:
                return None
            if is_real_country_code(alias_code):
                return alias_code
        if upper in _AMBIGUOUS_COUNTRY_CODE_TOKENS and not allow_ambiguous_codes:
            return None
        if is_real_country_code(upper):
            return upper
        return None

    return COUNTRY_NAME_TO_CODE.get(normalize_country_name_key(normalized))


def _special_locality_country_from_piece(value: str | None) -> str | None:
    for variant in _piece_variants(value):
        key = normalize_country_name_key(variant)
        if key in SPECIAL_LOCALITY_TO_COUNTRY:
            return SPECIAL_LOCALITY_TO_COUNTRY[key]
    return None


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


def _infer_country_from_city_piece(value: str | None, *, admin_piece: str | None = None) -> str | None:
    for variant in _piece_variants(value):
        city_key = _normalize_key(variant)
        if not city_key:
            continue

        records = list(_city_records_by_name().get(city_key) or [])
        if not records:
            continue

        admin_value = _normalize_text(admin_piece).upper()
        if admin_value:
            matching_admin_records = [item for item in records if str(item.get("admin1") or "").upper() == admin_value]
            if matching_admin_records:
                codes = {
                    str(item.get("country_code") or "").upper()
                    for item in matching_admin_records
                    if item.get("country_code")
                }
                if len(codes) == 1:
                    return next(iter(codes))
                dominant = _dominant_country_from_records(matching_admin_records)
                if dominant:
                    return dominant

        dominant = _dominant_country_from_records(records)
        if dominant:
            return dominant

    return None


def _infer_country_from_subdivision_pattern(pieces: list[str], normalized_location: str) -> str | None:
    if _WASHINGTON_DC_RE.search(normalized_location):
        return "US"

    for piece in pieces:
        special_country = _special_locality_country_from_piece(piece)
        if special_country:
            return special_country

    if len(pieces) < 2:
        return None

    region_piece = pieces[1]
    region_country = region_country_from_piece(region_piece)
    if region_country:
        return region_country

    if _SUBREGION_HINT_RE.search(region_piece):
        first_country = _infer_country_from_city_piece(pieces[0], admin_piece=None)
        if first_country:
            return first_country

        for piece in pieces:
            special_country = _special_locality_country_from_piece(piece)
            if special_country in _US_SUBREGION_COUNTRIES:
                return special_country

    if len(pieces) == 2 and not _explicit_country_from_piece(region_piece):
        first_country = _infer_country_from_city_piece(pieces[0], admin_piece=region_piece)
        second_country = _infer_country_from_city_piece(pieces[1], admin_piece=None) or _special_locality_country_from_piece(pieces[1])
        if first_country and second_country and first_country == second_country:
            return first_country
        if first_country == "US":
            return "US"
        if second_country == "US":
            return "US"

    return None


def _infer_country_from_city_dataset(location: str) -> str | None:
    pieces = _split_location_pieces(location)
    if not pieces:
        return None

    candidates: list[str] = []
    for index, piece in enumerate(pieces):
        admin_piece = pieces[index + 1] if index + 1 < len(pieces) else None
        inferred = _infer_country_from_city_piece(piece, admin_piece=admin_piece)
        if not inferred:
            continue
        weight = 3 if index == 0 else 1
        candidates.extend([inferred] * weight)

    unique = {candidate for candidate in candidates if candidate}
    if len(unique) == 1:
        return next(iter(unique))

    first_piece_country = _infer_country_from_city_piece(pieces[0], admin_piece=pieces[1] if len(pieces) > 1 else None)
    if first_piece_country and candidates.count(first_piece_country) >= 3:
        return first_piece_country

    return None


def _explicit_country_code_piece(pieces: list[str]) -> str | None:
    for raw_piece in reversed(pieces):
        country_code = _explicit_country_from_piece(raw_piece, allow_ambiguous_codes=False)
        if country_code:
            return country_code
    return None


def _context_has_country_hint(location: str, country_code: str) -> bool:
    lowered = _normalize_key(location)
    if not lowered:
        return False
    for phrase in _COUNTRY_CONTEXT_PHRASES.get(country_code, ()):
        if phrase in lowered:
            return True
    return False


def _infer_country_from_postal_patterns(location: str, pieces: list[str]) -> str | None:
    normalized = _normalize_text(location)
    if not normalized:
        return None

    first_piece_country = _infer_country_from_city_piece(pieces[0], admin_piece=pieces[1] if len(pieces) > 1 else None) if pieces else None
    region_country = region_country_from_piece(pieces[1]) if len(pieces) > 1 else None

    for country_code, pattern in POSTAL_PATTERNS:
        if not pattern.search(normalized):
            continue

        if country_code == "CA":
            return "CA"
        if country_code == "GB":
            return "GB"
        if country_code == "US":
            if first_piece_country == "US" or region_country == "US" or "zip" in _normalize_key(location) or _context_has_country_hint(location, "US"):
                return "US"
        elif country_code == "AU":
            if first_piece_country == "AU" or region_country == "AU" or _context_has_country_hint(location, "AU"):
                return "AU"
        elif country_code == "DE":
            if first_piece_country == "DE" or region_country == "DE" or _context_has_country_hint(location, "DE"):
                return "DE"

    return None


def _infer_country_from_context_clues(location: str) -> str | None:
    normalized = _normalize_text(location)
    if not normalized:
        return None

    lowered = _normalize_key(normalized)

    for tld, country_code in sorted(COUNTRY_TLD_TO_CODE.items(), key=lambda item: -len(item[0])):
        if tld in lowered:
            return country_code

    for country_code, pattern in COUNTRY_CLUE_PATTERNS:
        if pattern.search(normalized):
            return country_code

    return None


def _provider_country_prior(provider: str | None) -> str | None:
    normalized = _normalize_key(provider)
    if not normalized:
        return None
    country_code = PROVIDER_COUNTRY_PRIORS.get(normalized)
    return country_code if is_real_country_code(country_code) else None


def normalize_job_location_country(location: str | None, *, provider: str | None = None) -> tuple[str | None, str | None]:
    normalized = _normalize_text(location)
    if not normalized:
        return _sentinel_country(_SENTINEL_REMOTE_GLOBAL)

    pieces = _split_location_pieces(normalized)

    country_code = _explicit_country_phrase_from_text(normalized)
    if country_code:
        return (country_code, _country_name_from_code(country_code))

    country_code = _infer_country_from_subdivision_pattern(pieces, normalized)
    if country_code:
        return (country_code, _country_name_from_code(country_code))

    country_code = _explicit_country_code_piece(pieces)
    if country_code:
        return (country_code, _country_name_from_code(country_code))

    country_code = _infer_country_from_city_dataset(normalized)
    if country_code:
        return (country_code, _country_name_from_code(country_code))

    country_code = _infer_country_from_postal_patterns(normalized, pieces)
    if country_code:
        return (country_code, _country_name_from_code(country_code))

    country_code = _infer_country_from_context_clues(normalized)
    if country_code:
        return (country_code, _country_name_from_code(country_code))

    country_code = _provider_country_prior(provider)
    if country_code:
        return (country_code, _country_name_from_code(country_code))

    if _is_location_agnostic(normalized):
        return _sentinel_country(_SENTINEL_REMOTE_GLOBAL)

    return _sentinel_country(_SENTINEL_UNCERTAIN)
