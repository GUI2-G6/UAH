from __future__ import annotations

import unittest
from unittest.mock import patch

from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import beta_access as beta_access_api
from app.db.base import Base
from app.models.beta_access_request import BetaAccessRequest
from app.schemas.beta_access import BetaAccessRequestCreate


class BetaAccessIntakeTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine, tables=[BetaAccessRequest.__table__])
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def _build_request(self, client_host: str = "127.0.0.1") -> Request:
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/public/beta-access",
                "headers": [],
                "client": (client_host, 12345),
                "server": ("testserver", 80),
                "scheme": "http",
            }
        )

    def test_request_beta_access_persists_normalized_request(self):
        payload = BetaAccessRequestCreate(
            email="  PERSON@Example.com ",
            full_name="  Test Person ",
            notes=" Looking for entry-level data roles ",
            source_surface=" landing_beta_access ",
        )

        response = beta_access_api.request_beta_access(
            payload=payload,
            request=self._build_request(),
            db=self.db,
        )

        self.assertEqual(response.message, "Thanks - your beta access request has been received.")
        saved = self.db.query(BetaAccessRequest).one()
        self.assertEqual(saved.email, "person@example.com")
        self.assertEqual(saved.full_name, "Test Person")
        self.assertEqual(saved.source_surface, "landing_beta_access")
        self.assertEqual(saved.notes, "Looking for entry-level data roles")

    def test_request_beta_access_enforces_rate_limits(self):
        payload = BetaAccessRequestCreate(email="rate-limit@example.com")

        with patch.object(beta_access_api, "enforce_ip_rate_limit") as ip_limit, patch.object(
            beta_access_api, "enforce_subject_rate_limit"
        ) as subject_limit:
            beta_access_api.request_beta_access(
                payload=payload,
                request=self._build_request("203.0.113.17"),
                db=self.db,
            )

        self.assertEqual(ip_limit.call_count, 1)
        self.assertEqual(subject_limit.call_count, 1)

    def test_request_beta_access_sends_notification_email_when_enabled(self):
        payload = BetaAccessRequestCreate(email="notify@example.com")

        with patch.object(beta_access_api.settings, "BETA_ACCESS_NOTIFY_EMAIL", "beta@uahapp.com"), patch.object(
            beta_access_api, "send_email"
        ) as send_email:
            beta_access_api.request_beta_access(
                payload=payload,
                request=self._build_request(),
                db=self.db,
            )

        self.assertEqual(send_email.call_count, 1)
        kwargs = send_email.call_args.kwargs
        self.assertEqual(kwargs["to"], "beta@uahapp.com")
        self.assertEqual(kwargs["subject"], "UAH beta access request")
        self.assertIn("notify@example.com", kwargs["text"])

    def test_request_beta_access_survives_email_send_failures(self):
        payload = BetaAccessRequestCreate(email="survive@example.com")

        with patch.object(beta_access_api.settings, "BETA_ACCESS_NOTIFY_EMAIL", "beta@uahapp.com"), patch.object(
            beta_access_api, "send_email", side_effect=RuntimeError("smtp down")
        ):
            response = beta_access_api.request_beta_access(
                payload=payload,
                request=self._build_request(),
                db=self.db,
            )

        self.assertEqual(response.message, "Thanks - your beta access request has been received.")
        self.assertEqual(self.db.query(BetaAccessRequest).count(), 1)
