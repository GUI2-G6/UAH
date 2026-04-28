from __future__ import annotations

import unittest
from types import SimpleNamespace

from fastapi import HTTPException

from app.api.gmail import (
    GmailFeedbackCreateRequest,
    _feedback_override_for_message,
    gmail_create_feedback,
)
from app.models.user import GmailFeedback, GmailSuppression


class _FakeFeedbackQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._rows)


class _FakeDb:
    def __init__(self):
        self.added = []
        self.feedback_rows = []
        self.suppression_rows = []

    def add(self, obj):
        self.added.append(obj)
        if isinstance(obj, GmailFeedback):
            obj.id = len(self.feedback_rows) + 1
            self.feedback_rows.append(obj)
        if isinstance(obj, GmailSuppression):
            obj.id = len(self.suppression_rows) + 1
            self.suppression_rows.append(obj)

    def query(self, model):
        if model is GmailFeedback:
            return _FakeFeedbackQuery(self.feedback_rows)
        return _FakeFeedbackQuery([])

    def commit(self):
        return None

    def refresh(self, _obj):
        return None


class GmailFeedbackApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_feedback_override_matches_by_source_id_first(self):
        row = SimpleNamespace(
            source_id="abc123",
            sender_domain="example.com",
            subject_key="application update",
            company_key="example co",
            triage_label="relevant",
            override_status="offer",
        )
        override = _feedback_override_for_message(
            [row],
            source_id="abc123",
            sender_domain="other.com",
            subject_key="other",
            company_key="other",
        )
        self.assertEqual(override, "offer")

    async def test_rejects_invalid_triage_label(self):
        db = _FakeDb()
        user = SimpleNamespace(id=9)
        with self.assertRaises(HTTPException):
            await gmail_create_feedback(
                GmailFeedbackCreateRequest(
                    source_id="abc",
                    triage_label="bad_value",
                ),
                db=db,
                current_user=user,
            )

    async def test_not_relevant_feedback_creates_message_and_thread_suppressions(self):
        db = _FakeDb()
        user = SimpleNamespace(id=9)
        response = await gmail_create_feedback(
            GmailFeedbackCreateRequest(
                source_id="abc123",
                from_header="Granite <do-not-reply@candidatecare.com>",
                subject="Additional Information Needed",
                company_hint="Granite Telecommunications",
                triage_label="not_relevant",
                false_positive_reason="Marketing-style blast",
            ),
            db=db,
            current_user=user,
        )
        self.assertEqual(response["feedback"]["triage_label"], "not_relevant")
        self.assertIsNotNone(response["suppression"])
        self.assertEqual(response["suppression"]["scope"], "message")
        self.assertEqual(len(response.get("suppressions") or []), 2)
        scopes = {row["scope"] for row in response["suppressions"]}
        self.assertEqual(scopes, {"message", "thread"})


if __name__ == "__main__":
    unittest.main()
