from __future__ import annotations

from datetime import datetime, timezone
import unittest

from app.schemas.job import NormalizedJob
from app.services.ingest import (
    build_short_description,
    compute_display_tier,
    compute_quality_score,
    quality_check,
)


def _job(**overrides) -> NormalizedJob:
    payload = {
        "provider": "the_muse",
        "provider_job_id": "123",
        "provider_url": "https://www.themuse.com/jobs/acme/software-engineer",
        "title": "Software Engineer",
        "company": "Acme",
        "company_url": "https://www.themuse.com/companies/acme",
        "location": "Huntsville, AL",
        "is_remote": False,
        "job_type": "full_time",
        "experience_level": "entry",
        "categories": ["Software Engineering"],
        "description": "Build backend APIs and data services for internal and external customers with clear documentation.",
        "published_at": datetime(2026, 4, 13, 12, 30, tzinfo=timezone.utc),
    }
    payload.update(overrides)
    return NormalizedJob(**payload)


class IngestServiceTests(unittest.TestCase):
    def test_quality_check_rejects_missing_core_fields_or_spam(self):
        missing_company_ok, _ = quality_check(_job(company=""))
        short_desc_ok, _ = quality_check(_job(description="too short"))
        spam_ok, _ = quality_check(_job(title="HIRING NOW!!! $$$"))

        self.assertFalse(missing_company_ok)
        self.assertFalse(short_desc_ok)
        self.assertFalse(spam_ok)

    def test_quality_check_adds_soft_flags(self):
        ok, flags = quality_check(
            _job(
                location="",
                company_url="",
                categories=[],
                description="This description is long enough to store but intentionally not very detailed for scoring deductions only.",
                published_at=None,
            )
        )

        self.assertTrue(ok)
        self.assertIn("no_location", flags)
        self.assertIn("no_company_url", flags)
        self.assertIn("missing_categories", flags)
        self.assertIn("missing_published_date", flags)

    def test_quality_score_and_short_description_helpers(self):
        job = _job(company_url="", published_at=None, description="Word " * 80)
        _, flags = quality_check(job)
        score = compute_quality_score(job, flags)
        short = build_short_description("Word " * 80, max_length=40)

        self.assertGreaterEqual(score, 0.0)
        self.assertLess(score, 1.0)
        self.assertLessEqual(len(short), 40)

    def test_display_tier_windows(self):
        now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(
            compute_display_tier(is_active=True, last_seen_at=datetime(2026, 4, 1, tzinfo=timezone.utc), reference_time=now),
            "active",
        )
        self.assertEqual(
            compute_display_tier(is_active=True, last_seen_at=datetime(2026, 2, 20, tzinfo=timezone.utc), reference_time=now),
            "aging",
        )
        self.assertEqual(
            compute_display_tier(is_active=False, last_seen_at=datetime(2026, 4, 1, tzinfo=timezone.utc), reference_time=now),
            "hidden",
        )


if __name__ == "__main__":
    unittest.main()
