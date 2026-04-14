from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
import os
import re
from typing import Dict, Iterable, List, Optional

import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.muse_location import MuseSupportedLocation

MUSE_API_KEY = os.getenv("MUSE_API_KEY")
MUSE_JOBS_URL = "https://www.themuse.com/api/public/jobs"

REMOTE_LIKE_PATTERN = re.compile(r"\b(remote|hybrid|work\s*from\s*home|anywhere|flexible)\b", re.IGNORECASE)
US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "IA", "ID", "IL", "IN", "KS", "KY",
    "LA", "MA", "MD", "ME", "MI", "MN", "MO", "MS", "MT", "NC", "ND", "NE", "NH", "NJ", "NM", "NV", "NY",
    "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VA", "VT", "WA", "WI", "WV", "WY", "DC",
}
COUNTRY_NAME_TO_CODE = {
    "united states": "US",
    "usa": "US",
    "us": "US",
    "canada": "CA",
    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "germany": "DE",
    "france": "FR",
    "ireland": "IE",
    "australia": "AU",
    "new zealand": "NZ",
    "india": "IN",
    "singapore": "SG",
    "netherlands": "NL",
    "poland": "PL",
    "spain": "ES",
    "italy": "IT",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "switzerland": "CH",
    "mexico": "MX",
    "brazil": "BR",
    "japan": "JP",
}
COUNTRY_CODE_TO_NAME = {
    "US": "United States",
    "CA": "Canada",
    "GB": "United Kingdom",
    "DE": "Germany",
    "FR": "France",
    "IE": "Ireland",
    "AU": "Australia",
    "NZ": "New Zealand",
    "IN": "India",
    "SG": "Singapore",
    "NL": "Netherlands",
    "PL": "Poland",
    "ES": "Spain",
    "IT": "Italy",
    "SE": "Sweden",
    "NO": "Norway",
    "DK": "Denmark",
    "FI": "Finland",
    "CH": "Switzerland",
    "MX": "Mexico",
    "BR": "Brazil",
    "JP": "Japan",
}


def _normalize_location_name(name: str) -> str:
    return " ".join((name or "").strip().split())


def _normalize_key(name: str) -> str:
    return _normalize_location_name(name).lower()


def _infer_country_code(location_name: str) -> Optional[str]:
    normalized = _normalize_location_name(location_name)
    if not normalized:
        return None

    pieces = [part.strip() for part in normalized.split(",") if part.strip()]
    tail = pieces[-1].lower() if pieces else ""

    if tail:
        if len(tail) == 2 and tail.upper() in US_STATE_CODES:
            return "US"
        if len(tail) == 2 and tail.upper() in COUNTRY_CODE_TO_NAME:
            return tail.upper()
        if tail in COUNTRY_NAME_TO_CODE:
            return COUNTRY_NAME_TO_CODE[tail]

    for phrase, code in COUNTRY_NAME_TO_CODE.items():
        if re.search(rf"\b{re.escape(phrase)}\b", normalized.lower()):
            return code

    return None


def _extract_candidate_locations(job: dict) -> Iterable[str]:
    for item in (job.get("locations") or []):
        if not isinstance(item, dict):
            continue
        raw = _normalize_location_name(item.get("name") or "")
        if not raw:
            continue
        if REMOTE_LIKE_PATTERN.search(raw):
            continue
        yield raw


def _is_refresh_due(db: Session, now: datetime) -> bool:
    if settings.MUSE_LOCATION_INDEX_REFRESH_HOURS <= 0:
        return True

    most_recent = db.query(func.max(MuseSupportedLocation.updated_at)).scalar()
    if most_recent is None:
        return True

    if most_recent.tzinfo is None:
        most_recent = most_recent.replace(tzinfo=timezone.utc)

    return most_recent < (now - timedelta(hours=settings.MUSE_LOCATION_INDEX_REFRESH_HOURS))


async def refresh_muse_location_index(force: bool = False) -> dict:
    if not settings.MUSE_LOCATION_INDEX_ENABLED:
        return {"status": "disabled"}

    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        if not force and not _is_refresh_due(db, now):
            return {"status": "fresh"}

        timeout_seconds = max(2.0, settings.MUSE_LOCATION_INDEX_TIMEOUT_SECONDS)
        max_pages = max(1, settings.MUSE_LOCATION_INDEX_SCAN_MAX_PAGES)

        location_counter: Counter[str] = Counter()
        sample_name_by_key: Dict[str, str] = {}
        country_by_key: Dict[str, str] = {}

        stop_reason = "max_pages"
        scanned_pages = 0

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            for page in range(1, max_pages + 1):
                params = [("page", page)]
                if MUSE_API_KEY:
                    params.append(("api_key", MUSE_API_KEY))

                response = await client.get(MUSE_JOBS_URL, params=params)
                if response.status_code != 200:
                    stop_reason = f"muse_status_{response.status_code}"
                    break

                payload = response.json()
                scanned_pages += 1
                jobs = payload.get("results") or []
                if not jobs:
                    stop_reason = "no_results"
                    break

                for job in jobs:
                    for location_name in _extract_candidate_locations(job):
                        key = _normalize_key(location_name)
                        if not key:
                            continue
                        location_counter[key] += 1
                        sample_name_by_key.setdefault(key, location_name)
                        if key not in country_by_key:
                            inferred = _infer_country_code(location_name)
                            if inferred:
                                country_by_key[key] = inferred

                page_count = payload.get("page_count") or page
                if page >= page_count:
                    stop_reason = "page_count_end"
                    break

        if not location_counter:
            return {
                "status": "empty",
                "pages_scanned": scanned_pages,
                "stop_reason": stop_reason,
            }

        existing_rows = db.query(MuseSupportedLocation).all()
        by_key = {row.normalized_key: row for row in existing_rows}

        for key, observed_count in location_counter.items():
            location_name = sample_name_by_key[key]
            country_code = country_by_key.get(key)
            if not country_code:
                continue

            row = by_key.get(key)
            if row is None:
                row = MuseSupportedLocation(
                    normalized_key=key,
                    location_name=location_name,
                    country_code=country_code,
                    country_name=COUNTRY_CODE_TO_NAME.get(country_code),
                    observed_count=int(observed_count),
                    active=True,
                    last_seen_at=now,
                )
                db.add(row)
                by_key[key] = row
            else:
                row.location_name = location_name
                row.country_code = country_code
                row.country_name = COUNTRY_CODE_TO_NAME.get(country_code)
                row.observed_count = int(observed_count)
                row.active = True
                row.last_seen_at = now

        retention_cutoff = now - timedelta(days=max(1, settings.MUSE_LOCATION_INDEX_RETENTION_DAYS))
        for row in by_key.values():
            row_last_seen = row.last_seen_at
            if row_last_seen and row_last_seen.tzinfo is None:
                row_last_seen = row_last_seen.replace(tzinfo=timezone.utc)
            if row_last_seen and row_last_seen < retention_cutoff:
                row.active = False

        db.commit()

        return {
            "status": "updated",
            "rows": len(location_counter),
            "pages_scanned": scanned_pages,
            "stop_reason": stop_reason,
        }
    except Exception as exc:
        db.rollback()
        return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


async def ensure_muse_location_index() -> dict:
    return await refresh_muse_location_index(force=False)


def list_supported_countries(db: Session) -> List[dict]:
    rows = (
        db.query(
            MuseSupportedLocation.country_code,
            MuseSupportedLocation.country_name,
            func.count(MuseSupportedLocation.id).label("location_count"),
        )
        .filter(MuseSupportedLocation.active.is_(True))
        .group_by(MuseSupportedLocation.country_code, MuseSupportedLocation.country_name)
        .order_by(func.count(MuseSupportedLocation.id).desc(), MuseSupportedLocation.country_code.asc())
        .all()
    )

    output: List[dict] = []
    for country_code, country_name, location_count in rows:
        if not country_code:
            continue
        output.append(
            {
                "code": country_code,
                "name": country_name or COUNTRY_CODE_TO_NAME.get(country_code, country_code),
                "location_count": int(location_count or 0),
            }
        )

    return output


def list_supported_locations_for_country(db: Session, country_code: str, limit: int = 200) -> List[dict]:
    cc = (country_code or "").strip().upper()
    if not cc:
        return []

    query = (
        db.query(MuseSupportedLocation)
        .filter(MuseSupportedLocation.active.is_(True), MuseSupportedLocation.country_code == cc)
        .order_by(MuseSupportedLocation.observed_count.desc(), MuseSupportedLocation.location_name.asc())
        .limit(max(1, min(limit, 500)))
    )
    rows = query.all()

    return [
        {
            "name": row.location_name,
            "country_code": row.country_code,
            "country": row.country_name or COUNTRY_CODE_TO_NAME.get(row.country_code, row.country_code),
            "observed_count": int(row.observed_count or 0),
            "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
        }
        for row in rows
    ]
