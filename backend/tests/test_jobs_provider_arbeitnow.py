from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from app.providers.arbeitnow import ArbeitnowJobProvider


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class ArbeitnowProviderTests(unittest.TestCase):
    def test_map_filters_keeps_page_and_optional_flags(self):
        provider = ArbeitnowJobProvider()
        params = provider.map_filters({"page": 2, "is_remote": True, "visa_sponsorship": True})

        self.assertEqual(params["page"], 2)
        self.assertTrue(params["remote"])
        self.assertTrue(params["visa_sponsorship"])

    def test_fetch_normalizes_payload_and_post_filters_remote(self):
        provider = ArbeitnowJobProvider()
        payload = {
            "data": [
                {
                    "slug": "backend-engineer",
                    "title": "Backend Engineer",
                    "company_name": "Acme GmbH",
                    "location": "Berlin",
                    "description": "<p>Build backend APIs and platform services for customers.</p>",
                    "remote": True,
                    "url": "https://jobs.ashbyhq.com/acme/123",
                    "job_types": ["full-time", "berufseinstieg"],
                    "tags": ["python", "backend"],
                    "created_at": 1713000000,
                },
                {
                    "slug": "office-manager",
                    "title": "Office Manager",
                    "company_name": "Acme GmbH",
                    "location": "Berlin",
                    "description": "<p>Support office operations.</p>",
                    "remote": False,
                    "url": "https://jobs.ashbyhq.com/acme/456",
                    "job_types": ["full-time"],
                    "tags": ["operations"],
                    "created_at": 1713000000,
                },
            ]
        }

        with patch("app.providers.arbeitnow.tracked_request", return_value=_FakeResponse(payload=payload)):
            jobs = provider.fetch({"page": 1, "is_remote": True})

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.provider, "arbeitnow")
        self.assertEqual(job.provider_job_id, "backend-engineer")
        self.assertEqual(job.apply_url, "https://jobs.ashbyhq.com/acme/123")
        self.assertTrue(job.is_remote)
        self.assertEqual(job.job_type, "full_time")
        self.assertEqual(job.experience_level, "entry")
        self.assertIn("Software Engineering", job.categories)
        self.assertEqual(job.published_at, datetime.fromtimestamp(1713000000, tz=timezone.utc))


if __name__ == "__main__":
    unittest.main()
