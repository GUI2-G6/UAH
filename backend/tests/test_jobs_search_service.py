from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from app.services.job_search import _serialize_job


class JobSearchServiceTests(unittest.TestCase):
    def test_serialize_job_includes_link_health_and_staleness_fields(self):
        row = SimpleNamespace(
            id="8b0a5e6d-8c2b-44b4-9d79-4c2f9b4b3f44",
            provider="the_muse",
            provider_job_id="12345",
            provider_url="https://www.themuse.com/jobs/acme/software-engineer",
            provider_url_status="good",
            apply_url="https://jobs.ashbyhq.com/acme/123",
            apply_url_status="good",
            apply_portal="ashby",
            source_tags=["provider:the_muse", "apply_portal:ashby"],
            title="Software Engineer",
            company="Acme",
            company_url=None,
            location="Remote",
            job_type="external",
            experience_level="mid",
            categories=["Software Engineering"],
            short_description="Build APIs.",
            description="Build APIs and workflow tooling.",
            is_remote=True,
            quality_score=0.91,
            display_tier="active",
            staleness_status="fresh",
            staleness_flags=[],
            published_at=datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc),
            is_featured=False,
            is_active=True,
        )

        payload = _serialize_job(row)

        self.assertEqual(payload["job_url"], row.provider_url)
        self.assertEqual(payload["apply_url"], row.apply_url)
        self.assertEqual(payload["apply_portal"], "ashby")
        self.assertEqual(payload["provider_url_status"], "good")
        self.assertEqual(payload["staleness_status"], "fresh")
        self.assertEqual(payload["source_tags"], ["provider:the_muse", "apply_portal:ashby"])


if __name__ == "__main__":
    unittest.main()
