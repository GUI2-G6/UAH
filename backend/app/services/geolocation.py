import json
import io
import math
import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import urlopen

import httpx  # type: ignore[import-not-found]


# Provider mapping notes:
# - "ipapi"  -> ip-api.com (endpoint: http://ip-api.com/json/{ip})
# - "ipstack" -> ipstack.com (endpoint: http://api.ipstack.com/{ip})
GEO_IP_PROVIDER = os.getenv("GEO_IP_PROVIDER", "ipapi").strip().lower()
IPSTACK_API_KEY = os.getenv("IPSTACK_API_KEY", "").strip()
NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "UAH-JobBoard-Geolocation/1.0")

MILES_TO_KM = 1.609344
KM_TO_MILES = 0.621371
EARTH_RADIUS_MILES = 3959.0

CITIES_DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "cities.json"
GEONAMES_URL = "https://download.geonames.org/export/dump/cities1000.zip"

_CITY_CACHE: Optional[List[Dict[str, Any]]] = None

# Fallback list used if cities.json is absent.
FALLBACK_CITIES = [
    {"name": "New York", "admin1": "NY", "country_code": "US", "country": "United States", "lat": 40.7128, "lon": -74.0060, "population": 8804190},
    {"name": "Boston", "admin1": "MA", "country_code": "US", "country": "United States", "lat": 42.3601, "lon": -71.0589, "population": 675647},
    {"name": "Cambridge", "admin1": "MA", "country_code": "US", "country": "United States", "lat": 42.3736, "lon": -71.1097, "population": 118403},
    {"name": "Somerville", "admin1": "MA", "country_code": "US", "country": "United States", "lat": 42.3876, "lon": -71.0995, "population": 81045},
    {"name": "Brookline", "admin1": "MA", "country_code": "US", "country": "United States", "lat": 42.3318, "lon": -71.1212, "population": 62820},
    {"name": "Los Angeles", "admin1": "CA", "country_code": "US", "country": "United States", "lat": 34.0522, "lon": -118.2437, "population": 3898747},
    {"name": "San Francisco", "admin1": "CA", "country_code": "US", "country": "United States", "lat": 37.7749, "lon": -122.4194, "population": 808988},
    {"name": "Chicago", "admin1": "IL", "country_code": "US", "country": "United States", "lat": 41.8781, "lon": -87.6298, "population": 2746388},
    {"name": "Toronto", "admin1": "ON", "country_code": "CA", "country": "Canada", "lat": 43.6532, "lon": -79.3832, "population": 2731571},
    {"name": "Vancouver", "admin1": "BC", "country_code": "CA", "country": "Canada", "lat": 49.2827, "lon": -123.1207, "population": 675218},
    {"name": "Montreal", "admin1": "QC", "country_code": "CA", "country": "Canada", "lat": 45.5019, "lon": -73.5674, "population": 1762949},
    {"name": "London", "admin1": "ENG", "country_code": "GB", "country": "United Kingdom", "lat": 51.5072, "lon": -0.1276, "population": 8982000},
    {"name": "Manchester", "admin1": "ENG", "country_code": "GB", "country": "United Kingdom", "lat": 53.4808, "lon": -2.2426, "population": 568996},
    {"name": "Birmingham", "admin1": "ENG", "country_code": "GB", "country": "United Kingdom", "lat": 52.4862, "lon": -1.8904, "population": 1141816},
    {"name": "Berlin", "admin1": "BE", "country_code": "DE", "country": "Germany", "lat": 52.52, "lon": 13.405, "population": 3669491},
    {"name": "Munich", "admin1": "BY", "country_code": "DE", "country": "Germany", "lat": 48.1371, "lon": 11.5754, "population": 1488202},
    {"name": "Paris", "admin1": "IDF", "country_code": "FR", "country": "France", "lat": 48.8566, "lon": 2.3522, "population": 2102650},
    {"name": "Lyon", "admin1": "ARA", "country_code": "FR", "country": "France", "lat": 45.764, "lon": 4.8357, "population": 522250},
]


def _env_bool(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def miles_to_km(miles: float) -> float:
    return miles * MILES_TO_KM


def km_to_miles(km: float) -> float:
    return km * KM_TO_MILES


def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2) ** 2)
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_MILES * c


def _normalize_city_record(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        lat = float(row.get("lat"))
        lon = float(row.get("lon"))
    except (TypeError, ValueError):
        return None

    name = (row.get("name") or "").strip()
    if not name:
        return None

    country_code = (row.get("country_code") or "").strip().upper()
    country = (row.get("country") or "").strip()
    admin1 = (row.get("admin1") or "").strip()

    population_raw = row.get("population")
    try:
        population = int(population_raw) if population_raw is not None else 0
    except (TypeError, ValueError):
        population = 0

    return {
        "name": name,
        "admin1": admin1,
        "country_code": country_code,
        "country": country,
        "lat": lat,
        "lon": lon,
        "population": population,
    }


def load_city_dataset(force_reload: bool = False) -> List[Dict[str, Any]]:
    global _CITY_CACHE
    if _CITY_CACHE is not None and not force_reload:
        return _CITY_CACHE

    cities: List[Dict[str, Any]] = []
    if CITIES_DATA_PATH.exists():
        try:
            raw = json.loads(CITIES_DATA_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                for item in raw:
                    if isinstance(item, dict):
                        normalized = _normalize_city_record(item)
                        if normalized:
                            cities.append(normalized)
        except Exception:
            cities = []

    if not cities:
        cities = [dict(item) for item in FALLBACK_CITIES]

    _CITY_CACHE = cities
    return cities


def _parse_geonames_rows(raw_text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in raw_text.splitlines():
        if not line.strip():
            continue

        parts = line.split("\t")
        if len(parts) < 15:
            continue

        name = parts[1].strip()
        lat_raw = parts[4].strip()
        lon_raw = parts[5].strip()
        country_code = parts[8].strip().upper()
        admin1 = parts[10].strip()
        population_raw = parts[14].strip() or "0"

        if not name or not lat_raw or not lon_raw:
            continue

        try:
            lat = float(lat_raw)
            lon = float(lon_raw)
            population = int(population_raw)
        except ValueError:
            continue

        rows.append(
            {
                "name": name,
                "lat": lat,
                "lon": lon,
                "country_code": country_code,
                "admin1": admin1,
                "population": population,
                "country": "",
            }
        )

    rows.sort(key=lambda x: (x["country_code"], -x["population"], x["name"]))
    return rows


def build_city_dataset_from_geonames(timeout_seconds: int = 90) -> Dict[str, Any]:
    response = urlopen(GEONAMES_URL, timeout=timeout_seconds)
    payload = response.read()

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        raw = archive.read("cities1000.txt").decode("utf-8")

    rows = _parse_geonames_rows(raw)
    CITIES_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    CITIES_DATA_PATH.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")

    return {
        "cities_written": len(rows),
        "path": str(CITIES_DATA_PATH),
        "size_bytes": CITIES_DATA_PATH.stat().st_size,
    }


def ensure_city_dataset() -> Dict[str, Any]:
    """
    Ensure cities dataset exists at startup.

    - Controlled by env `GEOLOCATION_AUTO_BUILD_DATASET` (default: true).
    - If build fails, caller can continue with fallback cities.
    """
    auto_build = _env_bool("GEOLOCATION_AUTO_BUILD_DATASET", "true")
    timeout_seconds = int(os.getenv("GEOLOCATION_DATASET_TIMEOUT_SECONDS", "90"))

    if CITIES_DATA_PATH.exists():
        return {
            "status": "existing",
            "path": str(CITIES_DATA_PATH),
            "size_bytes": CITIES_DATA_PATH.stat().st_size,
        }

    if not auto_build:
        return {
            "status": "skipped",
            "reason": "auto-build disabled",
            "path": str(CITIES_DATA_PATH),
        }

    try:
        result = build_city_dataset_from_geonames(timeout_seconds=timeout_seconds)
        # Warm in-memory cache with freshly built dataset.
        load_city_dataset(force_reload=True)
        return {"status": "built", **result}
    except Exception as exc:
        return {
            "status": "failed",
            "error": str(exc),
            "fallback_city_count": len(FALLBACK_CITIES),
        }


async def _ipapi_lookup(client_ip: Optional[str]) -> Dict[str, Any]:
    query = client_ip or ""
    url = f"http://ip-api.com/json/{query}"
    params = {
        "fields": "status,message,country,countryCode,regionName,city,lat,lon,query",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        raise RuntimeError(f"ip-api request failed ({resp.status_code})")

    data = resp.json()
    if data.get("status") != "success":
        raise RuntimeError(data.get("message") or "ip-api lookup failed")

    lat = data.get("lat")
    lon = data.get("lon")
    if lat is None or lon is None:
        raise RuntimeError("ip-api response missing coordinates")

    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "city": data.get("city") or "",
        "country": data.get("country") or "",
        "country_code": (data.get("countryCode") or "").upper(),
        "region": data.get("regionName") or "",
        "source": "ip-api",
        "accuracy_km": 50,
    }


async def _ipstack_lookup(client_ip: Optional[str]) -> Dict[str, Any]:
    if not IPSTACK_API_KEY:
        raise RuntimeError("ipstack key missing")

    query = client_ip or "check"
    url = f"http://api.ipstack.com/{query}"
    params = {"access_key": IPSTACK_API_KEY}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        raise RuntimeError(f"ipstack request failed ({resp.status_code})")

    data = resp.json()
    if data.get("success") is False:
        info = data.get("error", {}).get("info")
        raise RuntimeError(info or "ipstack lookup failed")

    lat = data.get("latitude")
    lon = data.get("longitude")
    if lat is None or lon is None:
        raise RuntimeError("ipstack response missing coordinates")

    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "city": data.get("city") or "",
        "country": data.get("country_name") or "",
        "country_code": (data.get("country_code") or "").upper(),
        "region": data.get("region_name") or "",
        "source": "ipstack",
        "accuracy_km": 50,
    }


async def reverse_geocode(lat: float, lon: float) -> Dict[str, Any]:
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "jsonv2",
        "lat": lat,
        "lon": lon,
        "addressdetails": 1,
    }
    headers = {"User-Agent": NOMINATIM_USER_AGENT}

    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.get(url, params=params, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(f"nominatim reverse lookup failed ({resp.status_code})")

    payload = resp.json()
    address = payload.get("address", {})

    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or ""
    )
    country = address.get("country") or ""
    country_code = (address.get("country_code") or "").upper()

    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "city": city,
        "country": country,
        "country_code": country_code,
        "source": "nominatim-reverse",
        "accuracy_km": None,
    }


async def geocode_query(query: str, country_code: Optional[str] = None) -> Dict[str, Any]:
    text = (query or "").strip()
    if not text:
        raise RuntimeError("query is required")

    params: Dict[str, Any] = {
        "q": text,
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
    }
    if country_code:
        params["countrycodes"] = country_code.strip().lower()

    headers = {"User-Agent": NOMINATIM_USER_AGENT}
    url = "https://nominatim.openstreetmap.org/search"

    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.get(url, params=params, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(f"nominatim geocode failed ({resp.status_code})")

    payload = resp.json()
    if not payload:
        raise RuntimeError("no geocoding matches found")

    item = payload[0]
    address = item.get("address", {})
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or ""
    )

    return {
        "latitude": float(item["lat"]),
        "longitude": float(item["lon"]),
        "city": city,
        "country": address.get("country") or "",
        "country_code": (address.get("country_code") or "").upper(),
        "display_name": item.get("display_name") or text,
        "source": "nominatim-geocode",
    }


async def resolve_ip_location(client_ip: Optional[str]) -> Dict[str, Any]:
    provider = GEO_IP_PROVIDER if GEO_IP_PROVIDER in {"ipapi", "ipstack"} else "ipapi"
    primary_error: Optional[Exception] = None

    # Try explicitly selected provider first.
    try:
        if provider == "ipstack":
            return await _ipstack_lookup(client_ip)
        return await _ipapi_lookup(client_ip)
    except Exception as exc:
        primary_error = exc

    # Fallback behavior:
    # - If provider is ipapi, only try ipstack when a key is available.
    # - If provider is ipstack, always try ipapi fallback.
    try_fallback = False
    fallback_provider = ""
    if provider == "ipapi" and IPSTACK_API_KEY:
        try_fallback = True
        fallback_provider = "ipstack"
    elif provider == "ipstack":
        try_fallback = True
        fallback_provider = "ipapi"

    if try_fallback:
        try:
            if fallback_provider == "ipstack":
                return await _ipstack_lookup(client_ip)
            return await _ipapi_lookup(client_ip)
        except Exception as fallback_error:
            raise RuntimeError(
                f"{provider} failed: {primary_error}; {fallback_provider} fallback failed: {fallback_error}"
            )

    raise RuntimeError(f"{provider} failed: {primary_error}")


def find_cities_in_radius(
    latitude: float,
    longitude: float,
    radius_miles: float,
    country_code: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    radius_miles = max(0.1, float(radius_miles))
    country_filter = (country_code or "").strip().upper()

    output: List[Dict[str, Any]] = []
    for city in load_city_dataset():
        if country_filter and city.get("country_code") != country_filter:
            continue

        distance = haversine_distance_miles(latitude, longitude, city["lat"], city["lon"])
        if distance <= radius_miles:
            output.append(
                {
                    "name": city["name"],
                    "admin1": city.get("admin1") or "",
                    "country": city.get("country") or "",
                    "country_code": city.get("country_code") or "",
                    "latitude": city["lat"],
                    "longitude": city["lon"],
                    "population": city.get("population", 0),
                    "distance_miles": round(distance, 2),
                }
            )

    output.sort(key=lambda x: (x["distance_miles"], -(x.get("population") or 0), x["name"]))
    return output[: max(1, int(limit))]


def list_country_cities(country_code: str, limit: int = 120) -> List[Dict[str, Any]]:
    cc = (country_code or "").strip().upper()
    if not cc:
        return []

    cities = [
        city
        for city in load_city_dataset()
        if (city.get("country_code") or "").upper() == cc
    ]
    cities.sort(key=lambda x: (-(x.get("population") or 0), x.get("name") or ""))

    return [
        {
            "name": city["name"],
            "admin1": city.get("admin1") or "",
            "country": city.get("country") or "",
            "country_code": city.get("country_code") or "",
            "latitude": city["lat"],
            "longitude": city["lon"],
            "population": city.get("population", 0),
        }
        for city in cities[: max(1, int(limit))]
    ]
