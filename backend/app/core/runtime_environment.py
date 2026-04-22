"""Helpers for runtime environment decisions that need fail-closed behavior."""

from __future__ import annotations

import base64
import binascii
import secrets

_LOCAL_DOCS_ENVIRONMENTS = {"development", "dev", "local"}
_BETA_DOCS_AUTH_REALM = 'Basic realm="UAH Beta API Docs"'
_INTERNAL_SURFACE_ENVIRONMENTS = {"beta", "staging", "prod", "production"}
_INTERNAL_SURFACE_PREFIXES = (
    "/api/admin",
    "/api/jobs/debug",
)
_INTERNAL_SURFACE_EXACT_PATHS = {
    "/api/diagnostics",
    "/api/geolocation/muse-supported-locations/refresh",
}


def normalize_runtime_environment(raw_environment: str | None) -> str:
    return (raw_environment or "").strip().lower()


def generated_docs_basic_auth_enabled(
    raw_environment: str | None,
    docs_passcode: str | None,
) -> bool:
    environment = normalize_runtime_environment(raw_environment)
    return environment == "beta" and bool((docs_passcode or "").strip())


def generated_docs_enabled(
    raw_environment: str | None,
    docs_passcode: str | None = None,
) -> bool:
    """Expose generated docs for local/dev, or beta when auth-gated."""

    environment = normalize_runtime_environment(raw_environment)
    return environment in _LOCAL_DOCS_ENVIRONMENTS or generated_docs_basic_auth_enabled(
        environment,
        docs_passcode,
    )


def is_generated_docs_path(path: str | None) -> bool:
    normalized_path = (path or "").split("?", 1)[0].strip()
    return (
        normalized_path == "/docs"
        or normalized_path.startswith("/docs/")
        or normalized_path == "/redoc"
        or normalized_path.startswith("/redoc/")
        or normalized_path == "/openapi.json"
    )


def generated_docs_basic_auth_authorized(
    authorization_header: str | None,
    expected_username: str,
    expected_passcode: str,
) -> bool:
    if not authorization_header:
        return False

    scheme, _, encoded_credentials = authorization_header.partition(" ")
    if scheme.strip().lower() != "basic" or not encoded_credentials.strip():
        return False

    try:
        decoded_credentials = base64.b64decode(
            encoded_credentials.strip(),
            validate=True,
        ).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return False

    username, separator, passcode = decoded_credentials.partition(":")
    if separator != ":":
        return False

    return secrets.compare_digest(username, expected_username) and secrets.compare_digest(
        passcode,
        expected_passcode,
    )


def generated_docs_authenticate_header() -> str:
    return _BETA_DOCS_AUTH_REALM


def generated_docs_auth_required(
    path: str | None,
    raw_environment: str | None,
    authorization_header: str | None,
    expected_username: str,
    expected_passcode: str | None,
) -> bool:
    if not generated_docs_basic_auth_enabled(raw_environment, expected_passcode):
        return False

    if not is_generated_docs_path(path):
        return False

    normalized_passcode = (expected_passcode or "").strip()
    return not generated_docs_basic_auth_authorized(
        authorization_header=authorization_header,
        expected_username=expected_username,
        expected_passcode=normalized_passcode,
    )


def internal_surface_auth_enabled(
    raw_environment: str | None,
    internal_api_key: str | None,
) -> bool:
    environment = normalize_runtime_environment(raw_environment)
    return environment in _INTERNAL_SURFACE_ENVIRONMENTS and bool((internal_api_key or "").strip())


def is_internal_surface_path(path: str | None) -> bool:
    normalized_path = (path or "").split("?", 1)[0].strip()
    if not normalized_path:
        return False

    if normalized_path in _INTERNAL_SURFACE_EXACT_PATHS:
        return True

    for prefix in _INTERNAL_SURFACE_PREFIXES:
        if normalized_path == prefix or normalized_path.startswith(f"{prefix}/"):
            return True

    return False


def internal_surface_api_key_authorized(
    provided_key: str | None,
    expected_key: str,
) -> bool:
    normalized_expected = (expected_key or "").strip()
    normalized_provided = (provided_key or "").strip()
    if not normalized_expected:
        return False
    if not normalized_provided:
        return False
    return secrets.compare_digest(normalized_provided, normalized_expected)


def internal_surface_auth_required(
    path: str | None,
    raw_environment: str | None,
    provided_key: str | None,
    expected_key: str | None,
) -> bool:
    if not internal_surface_auth_enabled(raw_environment, expected_key):
        return False

    if not is_internal_surface_path(path):
        return False

    return not internal_surface_api_key_authorized(
        provided_key=provided_key,
        expected_key=(expected_key or "").strip(),
    )
