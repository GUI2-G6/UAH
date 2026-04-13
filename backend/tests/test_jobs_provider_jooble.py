from __future__ import annotations

import unittest
from unittest.mock import patch

from app.providers.jooble import JoobleJobProvider


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class JoobleProviderTests(unittest.TestCase):
    def test_map_filters_builds_post_body(self):
        provider = JoobleJobProvider()
        payload = provider.map_filters(
            {
                "page": 3,
                "keywords": "software engineer",
                "location": "Remote",
                "radius": "0",
                "salary": 120000,
                "companysearch": True,
            }
        )

        self.assertEqual(payload["page"], 3)
        self.assertEqual(payload["ResultOnPage"], provider.max_page_size)
        self.assertEqual(payload["keywords"], "software engineer")
        self.assertEqual(payload["location"], "Remote")
        self.assertEqual(payload["radius"], "0")
        self.assertEqual(payload["salary"], 120000)
        self.assertEqual(payload["companysearch"], "true")

    def test_fetch_keeps_negative_ids_as_strings_and_omits_published_at(self):
        provider = JoobleJobProvider()
        payload = {
            "jobs": [
                {
                    "id": -2572280757938267395,
                    "title": "Remote Software Engineer",
                    "company": "Acme",
                    "location": "Remote",
                    "snippet": "<b>Build</b> APIs and distributed systems.",
                    "type": "Full-time",
                    "link": "https://jooble.org/away/job/123",
                    "source": "linkedin",
                    "updated": "2026-04-13T00:00:00.0000000",
                }
            ]
        }

        with patch("app.providers.jooble.settings.JOOBLE_API_KEY", "demo-key"), patch(
            "app.providers.jooble.tracked_request",
            return_value=_FakeResponse(payload=payload),
        ):
            jobs = provider.fetch({"page": 1, "keywords": "software engineer", "location": "Remote"})

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.provider_job_id, "-2572280757938267395")
        self.assertIsNone(job.published_at)
        self.assertTrue(job.is_remote)
        self.assertEqual(job.provider_url, "https://jooble.org/away/job/123")


if __name__ == "__main__":
    unittest.main()
