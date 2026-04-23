from __future__ import annotations

import unittest
from unittest.mock import patch

from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import landing_feedback as landing_feedback_api
from app.db.base import Base
from app.models.landing_feedback_submission import LandingFeedbackSubmission
from app.schemas.landing_feedback import LandingFeedbackCreate


class LandingFeedbackIntakeTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine, tables=[LandingFeedbackSubmission.__table__])
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def _build_request(self, client_host: str = "127.0.0.1") -> Request:
        return Request(
            {
                "type": "http",
                "method": "POST",
                "path": "/api/public/landing-feedback",
                "headers": [],
                "client": (client_host, 12345),
                "server": ("testserver", 80),
                "scheme": "http",
            }
        )

    def test_submit_persists_normalized_payload(self):
        payload = LandingFeedbackCreate(
            email="  FEEDBACK@Example.com ",
            full_name="  Pat ",
            frustration="  slow replies ",
            features="  better filters ",
            notify_public=True,
            interested_beta=False,
            source_surface=" landing_wishlist ",
        )

        response = landing_feedback_api.submit_landing_feedback(
            payload=payload,
            request=self._build_request(),
            db=self.db,
        )

        self.assertIn("received", response.message.lower())
        saved = self.db.query(LandingFeedbackSubmission).one()
        self.assertEqual(saved.email, "feedback@example.com")
        self.assertEqual(saved.full_name, "Pat")
        self.assertEqual(saved.frustration, "slow replies")
        self.assertEqual(saved.features, "better filters")
        self.assertTrue(saved.notify_public)
        self.assertFalse(saved.interested_beta)
        self.assertEqual(saved.source_surface, "landing_wishlist")

    def test_submit_enforces_rate_limits(self):
        payload = LandingFeedbackCreate(email="rate@example.com")

        with patch.object(landing_feedback_api, "enforce_ip_rate_limit") as ip_limit, patch.object(
            landing_feedback_api, "enforce_subject_rate_limit"
        ) as subject_limit:
            landing_feedback_api.submit_landing_feedback(
                payload=payload,
                request=self._build_request("198.51.100.9"),
                db=self.db,
            )

        self.assertEqual(ip_limit.call_count, 1)
        self.assertEqual(subject_limit.call_count, 1)

    def test_submit_sends_notification_when_configured(self):
        payload = LandingFeedbackCreate(email="notify-feedback@example.com", frustration="x")

        with patch.object(landing_feedback_api.settings, "BETA_ACCESS_NOTIFY_EMAIL", "ops@uahapp.com"), patch.object(
            landing_feedback_api, "send_email"
        ) as send_email:
            landing_feedback_api.submit_landing_feedback(
                payload=payload,
                request=self._build_request(),
                db=self.db,
            )

        self.assertEqual(send_email.call_count, 1)
        kwargs = send_email.call_args.kwargs
        self.assertEqual(kwargs["to"], "ops@uahapp.com")
        self.assertEqual(kwargs["subject"], "UAH landing feedback")
        self.assertIn("notify-feedback@example.com", kwargs["text"])

    def test_submit_survives_email_send_failures(self):
        payload = LandingFeedbackCreate(email="survive-fb@example.com")

        with patch.object(landing_feedback_api.settings, "BETA_ACCESS_NOTIFY_EMAIL", "ops@uahapp.com"), patch.object(
            landing_feedback_api, "send_email", side_effect=RuntimeError("smtp down")
        ):
            landing_feedback_api.submit_landing_feedback(
                payload=payload,
                request=self._build_request(),
                db=self.db,
            )

        self.assertEqual(self.db.query(LandingFeedbackSubmission).count(), 1)
