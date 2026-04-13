from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import HTTPException, Response
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import account as account_api
from app.api import auth as auth_api
from app.api import deps as deps_api
from app.core import auth_cookie as auth_cookie_api
from app.core.rate_limit import reset_rate_limit_state
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.google.service import GoogleAuthService
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserLogin,
    VerifyEmailRequest,
)


def _build_request(client_host: str = "127.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "headers": [],
        "client": (client_host, 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


class AuthSecurityTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine, tables=[User.__table__])
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        reset_rate_limit_state()

    def tearDown(self):
        self.db.close()
        reset_rate_limit_state()

    def _create_user(self, **overrides) -> User:
        user = User(
            email=overrides.pop("email", "user@example.com"),
            username=overrides.pop("username", "user@example.com"),
            hashed_password=overrides.pop("hashed_password", hash_password("Password123!")),
            email_verified=overrides.pop("email_verified", False),
            is_active=overrides.pop("is_active", True),
            **overrides,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_password_reset_token_is_single_use(self):
        self._create_user(email="reset@example.com", username="reset@example.com")

        with patch.object(account_api.settings, "EMAILS_ENABLED", False), \
             patch.object(account_api.settings, "SECRET_KEY", "reset-secret-key"):
            forgot = account_api.forgot_password(
                payload=ForgotPasswordRequest(email="reset@example.com"),
                request=_build_request(),
                db=self.db,
            )
            token = forgot.message.split(": ", 1)[1]

            response = account_api.reset_password(
                payload=ResetPasswordRequest(token=token, new_password="NewPassword123!"),
                request=_build_request(),
                db=self.db,
            )

            self.assertEqual(response.message, "Password has been reset successfully")

            with self.assertRaises(HTTPException) as replay_error:
                account_api.reset_password(
                    payload=ResetPasswordRequest(token=token, new_password="AnotherPass123!"),
                    request=_build_request(),
                    db=self.db,
                )

        self.assertEqual(replay_error.exception.status_code, 400)

    def test_email_verification_token_is_bound_to_current_email(self):
        user = self._create_user(email="before@example.com", username="before@example.com", email_verified=False)

        with patch.object(account_api.settings, "EMAILS_ENABLED", False), \
             patch.object(account_api.settings, "SECRET_KEY", "verify-secret-key"):
            issued = account_api.send_verification_email(
                request=_build_request(),
                db=self.db,
                current_user=user,
            )
            token = issued.message.split(": ", 1)[1]

            user.email = "after@example.com"
            user.username = "after@example.com"
            self.db.commit()
            self.db.refresh(user)

            with self.assertRaises(HTTPException) as verify_error:
                account_api.verify_email(
                    payload=VerifyEmailRequest(token=token),
                    request=_build_request(),
                    db=self.db,
                )

        self.assertEqual(verify_error.exception.status_code, 400)

    def test_login_rate_limit_blocks_repeated_attempts(self):
        self._create_user(email="login@example.com", username="login@example.com")
        request = _build_request("203.0.113.8")

        with patch.object(auth_api, "LOGIN_IP_LIMIT", 2), \
             patch.object(auth_api, "LOGIN_IDENTIFIER_LIMIT", 2):
            with self.assertRaises(HTTPException) as first_error:
                auth_api.login(
                    payload=UserLogin(email="login@example.com", password="WrongPassword123!"),
                    request=request,
                    response=Response(),
                    db=self.db,
                )
            self.assertEqual(first_error.exception.status_code, 401)

            with self.assertRaises(HTTPException) as second_error:
                auth_api.login(
                    payload=UserLogin(email="login@example.com", password="WrongPassword123!"),
                    request=request,
                    response=Response(),
                    db=self.db,
                )
            self.assertEqual(second_error.exception.status_code, 401)

            with self.assertRaises(HTTPException) as limited_error:
                auth_api.login(
                    payload=UserLogin(email="login@example.com", password="WrongPassword123!"),
                    request=request,
                    response=Response(),
                    db=self.db,
                )

        self.assertEqual(limited_error.exception.status_code, 429)

    def test_login_sets_http_only_auth_cookie(self):
        self._create_user(email="cookie@example.com", username="cookie@example.com")
        response = Response()

        with patch.object(auth_cookie_api.settings, "AUTH_COOKIE_NAME", "uah_auth_test"), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_HTTPS_ONLY", True), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_SAMESITE", "lax"), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_PATH", "/"):
            auth_api.login(
                payload=UserLogin(email="cookie@example.com", password="Password123!"),
                request=_build_request(),
                response=response,
                db=self.db,
            )

        set_cookie = response.headers.get("set-cookie", "")
        self.assertIn("uah_auth_test=", set_cookie)
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("Secure", set_cookie)

    def test_request_token_dependency_accepts_auth_cookie(self):
        token = create_access_token(data={"sub": "123"})
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/api/auth/me",
                "headers": [(b"cookie", f"uah_auth_test={token}".encode("utf-8"))],
                "client": ("127.0.0.1", 12345),
                "server": ("testserver", 80),
                "scheme": "http",
            }
        )

        with patch.object(auth_cookie_api.settings, "AUTH_COOKIE_NAME", "uah_auth_test"):
            resolved = deps_api.get_request_token(request=request, bearer_token=None)

        self.assertEqual(resolved, token)

    def test_google_auto_link_requires_verified_email(self):
        self._create_user(email="google@example.com", username="google@example.com")

        with self.assertRaises(ValueError) as auth_error:
            GoogleAuthService.get_or_create_user(
                db=self.db,
                google_id="google-sub-123",
                email="google@example.com",
                full_name="Google User",
                picture_url=None,
                email_verified=False,
            )

        self.assertEqual(str(auth_error.exception), "email_not_verified")
