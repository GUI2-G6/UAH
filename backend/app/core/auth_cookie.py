from fastapi import Request, Response

from app.core.config import settings


def set_no_store_headers(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def set_auth_cookie(response: Response, token: str) -> None:
    set_no_store_headers(response)
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.SESSION_COOKIE_HTTPS_ONLY,
        samesite=settings.SESSION_COOKIE_SAMESITE,
        path=settings.SESSION_COOKIE_PATH,
        max_age=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
    )


def clear_auth_cookie(response: Response) -> None:
    set_no_store_headers(response)
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path=settings.SESSION_COOKIE_PATH,
        secure=settings.SESSION_COOKIE_HTTPS_ONLY,
        httponly=True,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )


def get_auth_cookie_token(request: Request) -> str | None:
    token = (request.cookies.get(settings.AUTH_COOKIE_NAME) or "").strip()
    return token or None
