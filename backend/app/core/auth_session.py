from __future__ import annotations

from datetime import timedelta

from fastapi import Request

from app.core.config import settings
from app.core.security import create_access_token

AUTH_CLIENT_HEADER = "X-UAH-Client"
DEFAULT_AUTH_CLIENT = "web"
EXTENSION_AUTH_CLIENT = "extension"


def normalize_auth_client(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized == EXTENSION_AUTH_CLIENT:
        return EXTENSION_AUTH_CLIENT
    return DEFAULT_AUTH_CLIENT


def resolve_auth_client(
    request: Request | None = None,
    *,
    query_client: str | None = None,
) -> str:
    if query_client and query_client.strip():
        return normalize_auth_client(query_client)
    if request is None:
        return DEFAULT_AUTH_CLIENT
    return normalize_auth_client(request.headers.get(AUTH_CLIENT_HEADER))


def access_token_expire_minutes_for_client(client: str | None = None) -> int:
    normalized = normalize_auth_client(client)
    if normalized == EXTENSION_AUTH_CLIENT:
        return max(int(settings.EXTENSION_ACCESS_TOKEN_EXPIRE_MINUTES), 1)
    return max(int(settings.ACCESS_TOKEN_EXPIRE_MINUTES), 1)


def access_token_expire_seconds_for_client(client: str | None = None) -> int:
    return access_token_expire_minutes_for_client(client) * 60


def create_access_token_for_client(data: dict, client: str | None = None) -> str:
    return create_access_token(
        data=data,
        expires_delta=timedelta(seconds=access_token_expire_seconds_for_client(client)),
    )
