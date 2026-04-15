"""Version-controlled opt-out registry helpers for provider removals."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import json

REGISTRY_PATH = Path(__file__).resolve().parent / "opt_out_registry.json"


def _utc_now_iso() -> str:
    """Return the current UTC timestamp as an ISO string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_base_url(base_url: str) -> str:
    """Return a canonical scheme-and-host representation for registry lookups."""
    raw_value = " ".join((base_url or "").split())
    if not raw_value:
        raise ValueError("base_url is required")
    if "://" not in raw_value:
        raw_value = f"https://{raw_value}"
    parsed = urlparse(raw_value)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Could not normalize base_url '{base_url}'")
    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValueError(f"Could not normalize base_url '{base_url}'")
    port = ""
    if parsed.port and parsed.port not in {80, 443}:
        port = f":{parsed.port}"
    return f"{parsed.scheme.lower()}://{hostname}{port}"


def _default_registry() -> dict[str, object]:
    """Return the default registry payload."""
    return {
        "_comment": (
            "Providers who have requested UAH stop indexing their content. "
            "Add provider base_url to opt out. Do not remove entries without "
            "explicit written confirmation from the provider."
        ),
        "opted_out": [],
        "opted_out_log": [],
    }


def _load_registry() -> dict[str, object]:
    """Load the committed opt-out registry from disk."""
    if not REGISTRY_PATH.exists():
        return _default_registry()
    with REGISTRY_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    payload.setdefault("_comment", _default_registry()["_comment"])
    payload.setdefault("opted_out", [])
    payload.setdefault("opted_out_log", [])
    return payload


def _write_registry(payload: dict[str, object]) -> None:
    """Persist the opt-out registry with an atomic replace."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = REGISTRY_PATH.with_suffix(".json.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    temporary_path.replace(REGISTRY_PATH)


def register_opt_out(
    provider_name: str,
    base_url: str,
    contact_email: str,
    date: str,
    notes: str,
) -> dict[str, object]:
    """Record a provider opt-out request and persist it to the registry."""
    canonical_base_url = _normalize_base_url(base_url)
    payload = _load_registry()
    opted_out = [str(value) for value in payload.get("opted_out", [])]
    if canonical_base_url not in opted_out:
        opted_out.append(canonical_base_url)
    payload["opted_out"] = opted_out

    log_entries = list(payload.get("opted_out_log", []))
    log_entries.append(
        {
            "action": "register",
            "provider_name": " ".join((provider_name or "").split()),
            "base_url": canonical_base_url,
            "contact_email": " ".join((contact_email or "").split()),
            "request_date": " ".join((date or "").split()),
            "notes": " ".join((notes or "").split()),
            "recorded_at_utc": _utc_now_iso(),
        }
    )
    payload["opted_out_log"] = log_entries
    _write_registry(payload)
    return payload


def check_opt_out(base_url: str) -> bool:
    """Return whether a provider base URL is currently opted out."""
    canonical_base_url = _normalize_base_url(base_url)
    payload = _load_registry()
    opted_out = {str(value) for value in payload.get("opted_out", [])}
    return canonical_base_url in opted_out


def list_opted_out() -> list[str]:
    """Return the canonical base URLs that are currently opted out."""
    payload = _load_registry()
    return [str(value) for value in payload.get("opted_out", [])]


def remove_opt_out(base_url: str, confirmation_notes: str) -> dict[str, object]:
    """Remove a provider from opt-out status with explicit confirmation notes."""
    normalized_notes = " ".join((confirmation_notes or "").split())
    if not normalized_notes:
        raise ValueError("confirmation_notes are required when removing an opt-out entry")

    canonical_base_url = _normalize_base_url(base_url)
    payload = _load_registry()
    payload["opted_out"] = [
        str(value) for value in payload.get("opted_out", []) if str(value) != canonical_base_url
    ]

    log_entries = list(payload.get("opted_out_log", []))
    log_entries.append(
        {
            "action": "remove",
            "base_url": canonical_base_url,
            "confirmation_notes": normalized_notes,
            "recorded_at_utc": _utc_now_iso(),
        }
    )
    payload["opted_out_log"] = log_entries
    _write_registry(payload)
    return payload


__all__ = [
    "check_opt_out",
    "list_opted_out",
    "register_opt_out",
    "remove_opt_out",
]
