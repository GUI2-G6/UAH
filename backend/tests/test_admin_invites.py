from __future__ import annotations

import unittest

from fastapi import Response
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

    def test_create_invite_sets_creator_and_defaults(self):
        invite = admin_api.create_invite(
            payload=InviteCreate(),
            db=self.db,
            current_user=self.admin_user,
        )

        self.assertEqual(invite.created_by, self.admin_user.id)
        self.assertTrue(invite.is_active)
        self.assertIsNone(invite.used_by)
        self.assertGreaterEqual(len(invite.code), 32)

    def test_batch_list_and_revoke_invites(self):
        invites = admin_api.create_invites_batch(
            payload=InviteBatchCreate(count=3),
            db=self.db,
            current_user=self.admin_user,
        )

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
            db=self.db,
            current_user=self.admin_user,
        )

        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 204)
        revoked = self.db.query(Invite).filter(Invite.code == invites[2].code).first()
        self.assertFalse(revoked.is_active)
