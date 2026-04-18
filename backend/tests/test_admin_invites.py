from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from fastapi import HTTPException, Response
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import admin as admin_api
from app.db.base import Base
from app.models.invite import Invite
from app.models.user import User
from app.schemas.invite import InviteBatchCreate, InviteCreate


class AdminInviteTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine, tables=[User.__table__, Invite.__table__])
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()
        self.admin_user = self._create_user(
            email="admin@example.com",
            username="admin@example.com",
            is_admin=True,
            email_verified=True,
        )
        self.member_user = self._create_user(
            email="member@example.com",
            username="member@example.com",
            email_verified=True,
        )

    def tearDown(self):
        self.db.close()

    def _create_user(self, **overrides) -> User:
        user = User(
            email=overrides.pop("email", "user@example.com"),
            username=overrides.pop("username", "user@example.com"),
            hashed_password=overrides.pop("hashed_password", "hashed-password"),
            is_admin=overrides.pop("is_admin", False),
            email_verified=overrides.pop("email_verified", False),
            is_active=overrides.pop("is_active", True),
            **overrides,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _build_request(self, client_host: str = "127.0.0.1") -> Request:
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/admin/invites",
                "headers": [],
                "client": (client_host, 12345),
                "server": ("testserver", 80),
                "scheme": "http",
            }
        )

    def test_create_invite_sets_creator_and_defaults(self):
        invite = admin_api.create_invite(
            payload=InviteCreate(),
            request=self._build_request(),
            db=self.db,
            current_user=self.admin_user,
        )

        self.assertEqual(invite.created_by, self.admin_user.id)
        self.assertTrue(invite.is_active)
        self.assertIsNone(invite.used_by)
        self.assertEqual(invite.max_uses, 1)
        self.assertEqual(invite.use_count, 0)
        self.assertIsNone(invite.name)
        self.assertGreaterEqual(len(invite.code), 32)

    def test_create_invite_supports_name_uses_and_relative_expiry(self):
        before = datetime.now(timezone.utc)
        invite = admin_api.create_invite(
            payload=InviteCreate(name="Campus Ambassadors", max_uses=3, expires_in="1w"),
            request=self._build_request(),
            db=self.db,
            current_user=self.admin_user,
        )

        self.assertEqual(invite.name, "Campus Ambassadors")
        self.assertEqual(invite.max_uses, 3)
        self.assertEqual(invite.use_count, 0)
        self.assertIsNotNone(invite.expires_at)
        before_comparison = before
        if invite.expires_at.tzinfo is None:
            before_comparison = before.replace(tzinfo=None)
        self.assertGreater(invite.expires_at, before_comparison)

    def test_create_invite_rejects_conflicting_expiry_inputs(self):
        with self.assertRaises(HTTPException) as create_error:
            admin_api.create_invite(
                payload=InviteCreate(expires_in="1w", expires_at=datetime.now(timezone.utc)),
                request=self._build_request(),
                db=self.db,
                current_user=self.admin_user,
            )

        self.assertEqual(create_error.exception.status_code, 400)

    def test_batch_list_and_revoke_invites(self):
        invites = admin_api.create_invites_batch(
            payload=InviteBatchCreate(count=3),
            request=self._build_request(),
            db=self.db,
            current_user=self.admin_user,
        )

        invites[0].use_count = 1
        invites[0].used_by = self.member_user.id
        invites[1].is_active = False
        self.db.commit()

        unused_active = admin_api.list_invites(
            used=False,
            active=True,
            db=self.db,
            current_user=self.admin_user,
        )
        self.assertEqual(len(unused_active), 1)
        self.assertEqual(unused_active[0].code, invites[2].code)

        used_any_status = admin_api.list_invites(
            used=True,
            active=None,
            db=self.db,
            current_user=self.admin_user,
        )
        self.assertEqual(len(used_any_status), 1)
        self.assertEqual(used_any_status[0].code, invites[0].code)

        response = admin_api.revoke_invite(
            code=invites[2].code,
            request=self._build_request(),
            db=self.db,
            current_user=self.admin_user,
        )

        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 204)
        revoked = self.db.query(Invite).filter(Invite.code == invites[2].code).first()
        self.assertFalse(revoked.is_active)

    def test_create_invite_enforces_rate_limits(self):
        with patch.object(admin_api, "enforce_ip_rate_limit") as ip_limit, patch.object(
            admin_api, "enforce_subject_rate_limit"
        ) as subject_limit:
            admin_api.create_invite(
                payload=InviteCreate(),
                request=self._build_request("203.0.113.10"),
                db=self.db,
                current_user=self.admin_user,
            )

        self.assertEqual(ip_limit.call_count, 1)
        self.assertEqual(subject_limit.call_count, 1)
