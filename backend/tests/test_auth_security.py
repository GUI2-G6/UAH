from __future__ import annotations

import unittest
from http.cookies import SimpleCookie
from math import ceil
from time import monotonic
from unittest.mock import patch

from fastapi import HTTPException, Response
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jose import jwt

from app.api import account as account_api
from app.api import auth as auth_api
from app.api import deps as deps_api
from app.api import routes as routes_api
from app.core import auth_cookie as auth_cookie_api
from app.core import auth_session as auth_session_api
from app.core import rate_limit as rate_limit_api
from app.core.rate_limit import reset_rate_limit_state
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.google.service import GoogleAuthService
from app.models.deleted_identity import DeletedIdentity
from app.models.invite import Invite
from app.models.user import SavedJob, User
from app.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    UserLogin,
    UserRegister,
    VerifyEmailRequest,
)


def _build_request(
    client_host: str = "127.0.0.1",
    *,
    headers: list[tuple[bytes, bytes]] | None = None,
    scheme: str = "http",
    path: str = "/test",
    session: dict | None = None,
) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": headers or [],
        "client": (client_host, 12345),
        "server": ("testserver", 80),
        "scheme": scheme,
    }
    if session is not None:
        scope["session"] = session
    return Request(scope)


def _extract_cookie_value(set_cookie_header: str, cookie_name: str) -> str:
    cookie = SimpleCookie()
    cookie.load(set_cookie_header)
    morsel = cookie.get(cookie_name)
    if morsel is None:
        raise AssertionError(f"Cookie '{cookie_name}' was not set")
    return morsel.value


def _token_lifetime_seconds(token: str) -> int:
    claims = jwt.get_unverified_claims(token)
    return int(claims["exp"]) - int(claims["iat"])


class _MockAsyncResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return dict(self._payload)


class _MockGoogleAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, data=None, **kwargs):
        return _MockAsyncResponse({"access_token": "google-oauth-access"})

    async def get(self, url, headers=None, **kwargs):
        return _MockAsyncResponse(
            {
                "sub": "google-sub-123",
                "email": "extension@example.com",
                "name": "Extension User",
                "picture": "https://example.com/avatar.png",
                "email_verified": True,
            },
            status_code=200,
        )


class _FakeRedisPipeline:
    def __init__(self, client):
        self.client = client
        self.operations = []

    def incr(self, key):
        self.operations.append(("incr", key))
        return self

    def ttl(self, key):
        self.operations.append(("ttl", key))
        return self

    def execute(self):
        results = []
        for operation, key in self.operations:
            if operation == "incr":
                results.append(self.client.incr(key))
            elif operation == "ttl":
                results.append(self.client.ttl(key))
        self.operations.clear()
        return results


class _FakeRedis:
    def __init__(self):
        self.values = {}
        self.expires_at = {}

    def _purge_expired(self, key):
        expires_at = self.expires_at.get(key)
        if expires_at is not None and expires_at <= monotonic():
            self.values.pop(key, None)
            self.expires_at.pop(key, None)

    def pipeline(self):
        return _FakeRedisPipeline(self)

    def ping(self):
        return True

    def incr(self, key):
        self._purge_expired(key)
        self.values[key] = int(self.values.get(key, 0)) + 1
        return self.values[key]

    def ttl(self, key):
        self._purge_expired(key)
        if key not in self.values:
            return -2
        expires_at = self.expires_at.get(key)
        if expires_at is None:
            return -1
        return max(0, int(ceil(expires_at - monotonic())))

    def expire(self, key, ttl_seconds):
        self._purge_expired(key)
        if key not in self.values:
            return False
        self.expires_at[key] = monotonic() + max(int(ttl_seconds), 1)
        return True

    def scan_iter(self, match=None):
        prefix = str(match or "").rstrip("*")
        keys = list(self.values.keys())
        for key in keys:
            self._purge_expired(key)
        for key in list(self.values.keys()):
            if not match or key.startswith(prefix):
                yield key

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.values:
                deleted += 1
            self.values.pop(key, None)
            self.expires_at.pop(key, None)
        return deleted


class AuthSecurityTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            bind=engine,
            tables=[
                User.__table__,
                Invite.__table__,
                DeletedIdentity.__table__,
                SavedJob.__table__,
            ],
        )
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
        fake_redis = _FakeRedis()

        with patch.object(rate_limit_api, "_get_redis_client", return_value=fake_redis), \
             patch.object(auth_api, "LOGIN_IP_LIMIT", 2), \
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

    def test_register_requires_valid_invite_and_marks_invite_used(self):
        inviter = self._create_user(
            email="inviter@example.com",
            username="inviter@example.com",
            email_verified=True,
        )
        invite = Invite(code="VALID-INVITE-CODE", created_by=inviter.id, is_active=True)
        self.db.add(invite)
        self.db.commit()

        with patch.object(account_api.settings, "EMAILS_ENABLED", False), \
             patch.object(auth_api.settings, "SECRET_KEY", "register-secret"), \
             patch.object(auth_cookie_api.settings, "AUTH_COOKIE_NAME", "uah_auth_test"), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_HTTPS_ONLY", True), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_SAMESITE", "lax"), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_PATH", "/"):
            result = auth_api.register(
                payload=UserRegister(
                    email="invitee@example.com",
                    password="Password123!",
                    first_name="Invite",
                    last_name="User",
                    invite_code="VALID-INVITE-CODE",
                ),
                request=_build_request(),
                response=Response(),
                db=self.db,
            )

        created_user = self.db.query(User).filter(User.email == "invitee@example.com").first()
        consumed_invite = self.db.query(Invite).filter(Invite.code == "VALID-INVITE-CODE").first()

        self.assertIsNotNone(created_user)
        self.assertEqual(result.user.email, "invitee@example.com")
        self.assertEqual(created_user.invite_code_used, "VALID-INVITE-CODE")
        self.assertEqual(consumed_invite.used_by, created_user.id)
        self.assertIsNotNone(consumed_invite.used_at)
        self.assertTrue(consumed_invite.is_active)
        self.assertIsNotNone(created_user.email_verify_token_id)
        self.assertFalse(created_user.email_verified)

    def test_register_rejects_invalid_invite_code(self):
        with self.assertRaises(HTTPException) as register_error:
            auth_api.register(
                payload=UserRegister(
                    email="missing-invite@example.com",
                    password="Password123!",
                    first_name="Missing",
                    last_name="Invite",
                    invite_code="MISSING-INVITE",
                ),
                request=_build_request(),
                response=Response(),
                db=self.db,
            )

        self.assertEqual(register_error.exception.status_code, 400)
        self.assertEqual(register_error.exception.detail, "Invalid or expired invite code")

    def test_login_rejects_unverified_email_accounts(self):
        self._create_user(
            email="pending@example.com",
            username="pending@example.com",
            email_verified=False,
        )

        with self.assertRaises(HTTPException) as login_error:
            auth_api.login(
                payload=UserLogin(email="pending@example.com", password="Password123!"),
                request=_build_request(),
                response=Response(),
                db=self.db,
            )

        self.assertEqual(login_error.exception.status_code, 403)
        self.assertEqual(login_error.exception.detail, auth_api.EMAIL_VERIFICATION_REQUIRED_MESSAGE)

    def test_login_sets_http_only_auth_cookie(self):
        self._create_user(email="cookie@example.com", username="cookie@example.com", email_verified=True)
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

    def test_web_login_uses_default_token_lifetime(self):
        self._create_user(email="default-ttl@example.com", username="default-ttl@example.com", email_verified=True)
        response = Response()

        with patch.object(auth_api.settings, "SECRET_KEY", "ttl-secret"), \
             patch.object(auth_api.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60), \
             patch.object(auth_api.settings, "EXTENSION_ACCESS_TOKEN_EXPIRE_MINUTES", 1440), \
             patch.object(auth_cookie_api.settings, "AUTH_COOKIE_NAME", "uah_auth_test"), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_HTTPS_ONLY", True), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_SAMESITE", "lax"), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_PATH", "/"):
            auth_api.login(
                payload=UserLogin(email="default-ttl@example.com", password="Password123!"),
                request=_build_request(),
                response=response,
                db=self.db,
            )

        set_cookie = response.headers.get("set-cookie", "")
        token = _extract_cookie_value(set_cookie, "uah_auth_test")
        self.assertIn("Max-Age=3600", set_cookie)
        self.assertEqual(_token_lifetime_seconds(token), 3600)

    def test_extension_login_uses_extension_token_lifetime(self):
        self._create_user(email="extension-ttl@example.com", username="extension-ttl@example.com", email_verified=True)
        response = Response()

        with patch.object(auth_api.settings, "SECRET_KEY", "extension-ttl-secret"), \
             patch.object(auth_api.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60), \
             patch.object(auth_api.settings, "EXTENSION_ACCESS_TOKEN_EXPIRE_MINUTES", 1440), \
             patch.object(auth_cookie_api.settings, "AUTH_COOKIE_NAME", "uah_auth_test"), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_HTTPS_ONLY", True), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_SAMESITE", "lax"), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_PATH", "/"):
            auth_api.login(
                payload=UserLogin(email="extension-ttl@example.com", password="Password123!"),
                request=_build_request(headers=[(b"x-uah-client", b"extension")]),
                response=response,
                db=self.db,
            )

        set_cookie = response.headers.get("set-cookie", "")
        token = _extract_cookie_value(set_cookie, "uah_auth_test")
        self.assertIn("Max-Age=86400", set_cookie)
        self.assertEqual(_token_lifetime_seconds(token), 86400)

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

    def test_google_oauth_requires_prelinked_account(self):
        with self.assertRaises(ValueError) as auth_error:
            GoogleAuthService.get_or_create_user(
                db=self.db,
                google_id="unlinked-google-sub",
                email="unlinked@example.com",
                full_name="Unlinked User",
                picture_url=None,
                email_verified=True,
            )

        self.assertEqual(str(auth_error.exception), "google_not_linked")

    def test_deleted_identity_allows_reregistration_with_valid_invite(self):
        deleted_user = self._create_user(
            email="deleted-local@example.com",
            username="deleted-local@example.com",
            email_verified=True,
        )
        account_api.delete_account(response=Response(), db=self.db, current_user=deleted_user)

        inviter = self._create_user(
            email="inviter-2@example.com",
            username="inviter-2@example.com",
            email_verified=True,
        )
        invite = Invite(code="REREGISTER-BLOCK", created_by=inviter.id, is_active=True)
        self.db.add(invite)
        self.db.commit()

        with patch.object(account_api.settings, "EMAILS_ENABLED", False):
            result = auth_api.register(
                payload=UserRegister(
                    email="deleted-local@example.com",
                    password="Password123!",
                    first_name="Retry",
                    last_name="User",
                    invite_code="REREGISTER-BLOCK",
                ),
                request=_build_request(),
                response=Response(),
                db=self.db,
            )

        recreated = self.db.query(User).filter(User.email == "deleted-local@example.com").first()
        self.assertIsNotNone(recreated)
        self.assertEqual(result.user.email, "deleted-local@example.com")

    def test_send_verification_email_prefers_link_message(self):
        user = self._create_user(
            email="verify-link@example.com",
            username="verify-link@example.com",
            email_verified=False,
        )

        with patch.object(account_api.settings, "EMAILS_ENABLED", True), \
             patch.object(account_api.settings, "PUBLIC_APP_URL", "https://dev.uahapp.com"), \
             patch.object(account_api, "send_email") as mock_send:
            result = account_api.send_verification_email(
                request=_build_request(),
                db=self.db,
                current_user=user,
            )

        self.assertEqual(result.message, "Verification email sent")
        self.assertTrue(mock_send.called)
        text = mock_send.call_args.kwargs.get("text", "")
        self.assertIn("/verify-email?token=", text)
        self.assertNotIn("Verification token:", text)

    def test_delete_account_records_tombstones_and_cleans_artifacts(self):
        creator = self._create_user(
            email="creator-cleanup@example.com",
            username="creator-cleanup@example.com",
            email_verified=True,
        )
        consumed = Invite(code="CONSUMED-INVITE", created_by=creator.id, used_by=creator.id, is_active=True)
        created = Invite(code="CREATED-INVITE", created_by=creator.id, is_active=True)
        self.db.add_all([consumed, created])
        self.db.flush()
        self.db.add(
            SavedJob(
                user_id=creator.id,
                title="Software Engineer",
                company="UAH",
                url="https://example.com/job/1",
            )
        )
        self.db.commit()

        account_api.delete_account(response=Response(), db=self.db, current_user=creator)

        self.assertIsNone(self.db.query(User).filter(User.id == creator.id).first())
        email_tombstone = self.db.query(DeletedIdentity).filter(DeletedIdentity.email == "creator-cleanup@example.com").first()
        self.assertIsNotNone(email_tombstone)
        remaining_created_invite = self.db.query(Invite).filter(Invite.code == "CREATED-INVITE").first()
        self.assertIsNone(remaining_created_invite)
        consumed_after = self.db.query(Invite).filter(Invite.code == "CONSUMED-INVITE").first()
        self.assertIsNone(consumed_after)
        self.assertEqual(self.db.query(SavedJob).filter(SavedJob.user_id == creator.id).count(), 0)

        reinvite_creator = self._create_user(
            email="reinvite@example.com",
            username="reinvite@example.com",
            email_verified=True,
        )
        reinvite = Invite(code="REENTRY-INVITE", created_by=reinvite_creator.id, is_active=True)
        self.db.add(reinvite)
        self.db.commit()

        with patch.object(account_api.settings, "EMAILS_ENABLED", False):
            reentry = auth_api.register(
                payload=UserRegister(
                    email="creator-cleanup@example.com",
                    password="Password123!",
                    first_name="Re",
                    last_name="Entry",
                    invite_code="REENTRY-INVITE",
                ),
                request=_build_request(),
                response=Response(),
                db=self.db,
            )
        self.assertEqual(reentry.user.email, "creator-cleanup@example.com")

    def test_extension_client_token_resolves_with_standard_auth_dependency(self):
        user = self._create_user(email="dependency@example.com", username="dependency@example.com")

        with patch.object(auth_session_api.settings, "SECRET_KEY", "dependency-secret"), \
             patch.object(auth_session_api.settings, "EXTENSION_ACCESS_TOKEN_EXPIRE_MINUTES", 1440):
            token = auth_session_api.create_access_token_for_client(
                data={"sub": str(user.id)},
                client="extension",
            )
            resolved_user = deps_api.get_current_user(db=self.db, token=token)

        self.assertEqual(resolved_user.id, user.id)


class GoogleOAuthExtensionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine, tables=[User.__table__, DeletedIdentity.__table__])
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    async def test_google_oauth_callback_extension_uses_extension_token_lifetime(self):
        linked_user = User(
            email="extension@example.com",
            username="extension@example.com",
            google_id="google-sub-123",
            email_verified=True,
            is_active=True,
        )
        self.db.add(linked_user)
        self.db.commit()

        session = {
            "oauth_state": "state-123",
            "oauth_mode": "login",
            "oauth_intent": "login",
            "oauth_next": "/home",
            "oauth_client": "extension",
        }
        request = _build_request(
            scheme="https",
            path="/api/auth/google/callback",
            session=session,
        )

        with patch.object(routes_api, "GOOGLE_CLIENT_ID", "google-client-id"), \
             patch.object(routes_api, "GOOGLE_CLIENT_SECRET", "google-client-secret"), \
             patch.object(routes_api, "GOOGLE_REDIRECT_URI", "https://dev.uahapp.com/api/auth/google/callback"), \
             patch.object(routes_api.settings, "PUBLIC_APP_URL", "https://dev.uahapp.com"), \
             patch.object(routes_api.settings, "SECRET_KEY", "google-extension-secret"), \
             patch.object(routes_api.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60), \
             patch.object(routes_api.settings, "EXTENSION_ACCESS_TOKEN_EXPIRE_MINUTES", 1440), \
             patch.object(auth_cookie_api.settings, "AUTH_COOKIE_NAME", "uah_auth_test"), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_HTTPS_ONLY", True), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_SAMESITE", "lax"), \
             patch.object(auth_cookie_api.settings, "SESSION_COOKIE_PATH", "/"), \
             patch.object(routes_api.httpx, "AsyncClient", _MockGoogleAsyncClient):
            response = await routes_api.google_oauth_callback(
                request=request,
                code="google-code",
                state="state-123",
                db=self.db,
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers.get("location"), "https://dev.uahapp.com/oauth-callback?next=%2Fhome&provider=google")
        set_cookie = response.headers.get("set-cookie", "")
        token = _extract_cookie_value(set_cookie, "uah_auth_test")
        self.assertIn("Max-Age=86400", set_cookie)
        self.assertEqual(_token_lifetime_seconds(token), 86400)
        self.assertIsNone(request.session.get("oauth_client"))

        resolved_user = self.db.query(User).filter(User.email == "extension@example.com").first()
        self.assertIsNotNone(resolved_user)
        self.assertEqual(resolved_user.id, linked_user.id)

    async def test_google_oauth_callback_rejects_unlinked_identity(self):
        session = {
            "oauth_state": "state-123",
            "oauth_mode": "login",
            "oauth_intent": "register",
            "oauth_next": "/home",
            "oauth_client": "web",
        }
        request = _build_request(
            scheme="https",
            path="/api/auth/google/callback",
            session=session,
        )

        with patch.object(routes_api, "GOOGLE_CLIENT_ID", "google-client-id"), \
             patch.object(routes_api, "GOOGLE_CLIENT_SECRET", "google-client-secret"), \
             patch.object(routes_api, "GOOGLE_REDIRECT_URI", "https://dev.uahapp.com/api/auth/google/callback"), \
             patch.object(routes_api.settings, "PUBLIC_APP_URL", "https://dev.uahapp.com"), \
             patch.object(routes_api.httpx, "AsyncClient", _MockGoogleAsyncClient):
            response = await routes_api.google_oauth_callback(
                request=request,
                code="google-code",
                state="state-123",
                db=self.db,
            )

        self.assertEqual(response.status_code, 307)
        self.assertIn("/register", response.headers.get("location", ""))
        self.assertIn("reason=google_not_linked", response.headers.get("location", ""))
        self.assertIsNone(self.db.query(User).filter(User.email == "extension@example.com").first())
