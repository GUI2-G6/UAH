from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

from app.api.auth import ADMIN_EMAIL, _ensure_admin_user
from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.models.user import User


class AdminBootstrapTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine, tables=[User.__table__])
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_ensure_admin_raises_without_password(self):
        with patch.dict(os.environ, {"ADMIN_BOOTSTRAP_PASSWORD": ""}, clear=False):
            with self.assertRaises(ValueError):
                _ensure_admin_user(self.db)

    def test_ensure_admin_creates_verified_admin_with_password(self):
        with patch.dict(os.environ, {"ADMIN_BOOTSTRAP_PASSWORD": "first-secret-password-ok"}, clear=False):
            user = _ensure_admin_user(self.db)

        self.assertEqual(user.email, "admincontact@uahapp.com")
        self.assertTrue(user.is_admin)
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertTrue(verify_password("first-secret-password-ok", user.hashed_password))

    def test_ensure_admin_updates_password_when_hash_already_exists(self):
        with patch.dict(os.environ, {"ADMIN_BOOTSTRAP_PASSWORD": "original-password-ok"}, clear=False):
            first = _ensure_admin_user(self.db)
        self.assertTrue(verify_password("original-password-ok", first.hashed_password))

        with patch.dict(os.environ, {"ADMIN_BOOTSTRAP_PASSWORD": "rotated-password-ok"}, clear=False):
            second = _ensure_admin_user(self.db)

        self.assertEqual(second.id, first.id)
        self.assertTrue(verify_password("rotated-password-ok", second.hashed_password))
        self.assertFalse(verify_password("original-password-ok", second.hashed_password))

    def test_ensure_admin_still_reconciles_when_another_admin_exists(self):
        other = User(
            email="other-admin@example.com",
            username="other-admin@example.com",
            hashed_password=hash_password("other-secret-ok"),
            is_active=True,
            is_admin=True,
            email_verified=True,
        )
        self.db.add(other)
        self.db.commit()

        with patch.dict(os.environ, {"ADMIN_BOOTSTRAP_PASSWORD": "contact-pass-ok"}, clear=False):
            contact = _ensure_admin_user(self.db)

        self.assertEqual(contact.email, "admincontact@uahapp.com")
        self.assertTrue(contact.is_admin)
        self.assertEqual(self.db.query(User).filter(User.is_admin.is_(True)).count(), 2)
        self.assertIsNotNone(
            self.db.query(User).filter(func.lower(User.email) == ADMIN_EMAIL.lower()).first()
        )
