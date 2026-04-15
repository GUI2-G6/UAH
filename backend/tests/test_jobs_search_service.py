from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from app.services.job_search import _serialize_job


def _job_row(provider_job_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id="8b0a5e6d-8c2b-44b4-9d79-4c2f9b4b3f44",
        provider="the_muse",
        provider_job_id=provider_job_id,
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
        location_country_code="US",
        location_country_name="United States",
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


class JobSearchServiceTests(unittest.TestCase):
    def test_serialize_job_includes_link_health_and_staleness_fields(self):
        row = _job_row("12345")

        payload = _serialize_job(row)

        self.assertEqual(payload["provider"], "the_muse")
        self.assertEqual(payload["provider_job_id"], "12345")
        self.assertEqual(payload["job_url"], row.provider_url)
        self.assertEqual(payload["apply_url"], row.apply_url)
        self.assertEqual(payload["apply_portal"], "ashby")
        self.assertEqual(payload["provider_url_status"], "good")
        self.assertEqual(payload["staleness_status"], "fresh")
        self.assertEqual(payload["source_tags"], ["provider:the_muse", "apply_portal:ashby"])
        self.assertEqual(payload["location_country_code"], "US")
        self.assertEqual(payload["location_country_name"], "United States")

    def test_serialize_job_preserves_compatibility_id_shape(self):
        numeric_payload = _serialize_job(_job_row("12345"))
        slug_payload = _serialize_job(_job_row("backend-python-engineer"))

        self.assertEqual(numeric_payload["id"], 12345)
        self.assertIsInstance(numeric_payload["id"], int)
        self.assertEqual(numeric_payload["provider_job_id"], "12345")
        self.assertIsInstance(numeric_payload["provider_job_id"], str)

        self.assertEqual(slug_payload["id"], "backend-python-engineer")
        self.assertIsInstance(slug_payload["id"], str)
        self.assertEqual(slug_payload["provider_job_id"], "backend-python-engineer")
        self.assertIsInstance(slug_payload["provider_job_id"], str)


if __name__ == "__main__":
    unittest.main()
