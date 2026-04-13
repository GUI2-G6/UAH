from __future__ import annotations

from datetime import datetime, timezone
import unittest
from unittest.mock import patch

from app.providers.the_muse import TheMuseJobProvider


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class TheMuseProviderTests(unittest.TestCase):
    def test_map_filters_expands_categories_and_keeps_page(self):
        provider = TheMuseJobProvider()
        with patch("app.providers.the_muse.settings.THE_MUSE_API_KEY", "demo-key"):
            params = provider.map_filters(
                {
                    "category": ["tech"],
                    "location": ["Huntsville, AL"],
                    "experience_level": ["Entry Level"],
                    "page": 3,
                }
            )

        self.assertIn("Software Engineer", params["category"])
        self.assertEqual(params["location"], ["Huntsville, AL"])
        self.assertEqual(params["level"], ["Entry Level"])
        self.assertEqual(params["page"], 3)
        self.assertEqual(params["api_key"], "demo-key")

    def test_fetch_normalizes_response_payload(self):
        provider = TheMuseJobProvider()
        payload = {
            "results": [
                {
                    "id": 7619281,
                    "name": "Software Engineer",
                    "type": "Full Time",
                    "company": {"name": "Acme", "href": "https://www.themuse.com/companies/acme"},
                    "locations": [{"name": "Remote"}],
                    "levels": [{"name": "Entry Level"}],
                    "categories": [{"name": "Software Engineering"}],
                    "contents": "<p>Build APIs and data pipelines for customers across the platform.</p>",
                    "refs": {"landing_page": "https://www.themuse.com/jobs/acme/software-engineer"},
                    "publication_date": "2026-04-13T12:30:00Z",
                }
            ]
        }

        with patch("app.providers.the_muse.tracked_request", return_value=_FakeResponse(payload=payload)):
            jobs = provider.fetch({"category": ["tech"], "page": 0})

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job.provider, "the_muse")
        self.assertEqual(job.provider_job_id, "7619281")
        self.assertEqual(job.title, "Software Engineer")
        self.assertEqual(job.company, "Acme")
        self.assertEqual(job.location, "Remote")
        self.assertTrue(job.is_remote)
        self.assertEqual(job.experience_level, "entry")
        self.assertEqual(job.categories, ["Software Engineering"])
        self.assertIn("Build APIs and data pipelines", job.description)
        self.assertEqual(job.provider_url, "https://www.themuse.com/jobs/acme/software-engineer")
        self.assertEqual(job.published_at, datetime(2026, 4, 13, 12, 30, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
