from __future__ import annotations

import unittest
from unittest.mock import patch

from app.models.user import User
from app.services import service_connections


class ServiceConnectionsTests(unittest.TestCase):
    def _make_user(self, **overrides) -> User:
        return User(
            id=overrides.pop("id", 1),
            email=overrides.pop("email", "service@example.com"),
            username=overrides.pop("username", "service@example.com"),
            hashed_password=overrides.pop("hashed_password", "mock-hash"),
            gmail_refresh_token=overrides.pop("gmail_refresh_token", None),
            gmail_email=overrides.pop("gmail_email", None),
            **overrides,
        )

    def test_gmail_summary_is_available_when_configured_and_disconnected(self):
        user = self._make_user()

        with patch.object(service_connections.settings, "GMAIL_CLIENT_ID", "client-id"), \
             patch.object(service_connections.settings, "GMAIL_CLIENT_SECRET", "client-secret"), \
             patch.object(service_connections.settings, "GMAIL_REDIRECT_URI", "https://beta.uahapp.com/api/integrations/gmail/callback"):
            summaries = service_connections.list_service_summaries(user)

        gmail = next(item for item in summaries if item.key == "gmail")
        self.assertEqual(gmail.status, "available")
        self.assertFalse(gmail.connected)
        self.assertEqual(gmail.primary_action.key, "connect")
        self.assertEqual(gmail.primary_action.href, "/api/integrations/gmail/connect/start")

    def test_gmail_summary_is_connected_when_mailbox_is_linked(self):
        user = self._make_user(
            gmail_refresh_token="encrypted-refresh-token",
            gmail_email="mailbox@example.com",
        )

        with patch.object(service_connections.settings, "GMAIL_CLIENT_ID", "client-id"), \
             patch.object(service_connections.settings, "GMAIL_CLIENT_SECRET", "client-secret"), \
             patch.object(service_connections.settings, "GMAIL_REDIRECT_URI", "https://beta.uahapp.com/api/integrations/gmail/callback"):
            detail = service_connections.get_service_detail(user, "gmail")

        self.assertTrue(detail.connected)
        self.assertEqual(detail.status, "connected")
        self.assertEqual(detail.account_label, "mailbox@example.com")
        self.assertEqual(detail.actions[0].key, "scan")
        self.assertEqual(detail.actions[1].key, "disconnect")

    def test_gmail_summary_reports_needs_attention_when_config_is_missing(self):
        user = self._make_user()

        with patch.object(service_connections.settings, "GMAIL_CLIENT_ID", ""), \
             patch.object(service_connections.settings, "GMAIL_CLIENT_SECRET", ""), \
             patch.object(service_connections.settings, "GMAIL_REDIRECT_URI", ""):
            summaries = service_connections.list_service_summaries(user)

        gmail = next(item for item in summaries if item.key == "gmail")
        self.assertEqual(gmail.status, "needs_attention")
        self.assertFalse(gmail.primary_action.enabled)
        self.assertEqual(gmail.primary_action.key, "unavailable")

    def test_placeholder_services_are_returned_as_coming_soon(self):
        user = self._make_user()

        with patch.object(service_connections.settings, "GMAIL_CLIENT_ID", "client-id"), \
             patch.object(service_connections.settings, "GMAIL_CLIENT_SECRET", "client-secret"), \
             patch.object(service_connections.settings, "GMAIL_REDIRECT_URI", "https://beta.uahapp.com/api/integrations/gmail/callback"):
            summaries = service_connections.list_service_summaries(user)

        calendar = next(item for item in summaries if item.key == "calendar_sync")
        resume_imports = next(item for item in summaries if item.key == "resume_imports")

        self.assertEqual(calendar.status, "coming_soon")
        self.assertEqual(calendar.availability, "coming_soon")
        self.assertFalse(calendar.primary_action.enabled)

        self.assertEqual(resume_imports.status, "coming_soon")
        self.assertEqual(resume_imports.availability, "coming_soon")
        self.assertEqual(resume_imports.primary_action.label, "Coming soon")


if __name__ == "__main__":
    unittest.main()
