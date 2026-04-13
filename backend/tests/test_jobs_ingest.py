from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from app.schemas.job import NormalizedJob
from app.services.ingest import (
    _build_job_payload,
    _evaluate_staleness,
    build_short_description,
    compute_dedup_hash,
    compute_content_fingerprint,
    compute_display_tier,
    compute_quality_score,
    needs_link_health_backfill,
    needs_stale_audit,
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
                provider_url="",
            )
        )

        self.assertTrue(ok)
        self.assertIn("no_location", flags)
        self.assertIn("no_company_url", flags)
        self.assertIn("missing_categories", flags)
        self.assertIn("missing_published_date", flags)
        self.assertIn("missing_provider_url", flags)

    def test_quality_score_and_short_description_helpers(self):
        job = _job(company_url="", published_at=None, description="Word " * 80)
        _, flags = quality_check(job)
        score = compute_quality_score(job, flags)
        short = build_short_description("Word " * 80, max_length=40)

        self.assertGreaterEqual(score, 0.0)
        self.assertLess(score, 1.0)
        self.assertLessEqual(len(short), 40)

    def test_compute_dedup_hash_normalizes_common_noise(self):
        first = compute_dedup_hash("Senior Software Engineer - Remote", "Acme, Inc.")
        second = compute_dedup_hash("Software Engineer", "Acme")

        self.assertIsNotNone(first)
        self.assertEqual(first, second)

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

    def test_content_fingerprint_changes_on_material_description_update(self):
        original = _job(description="Build APIs and data services for customers.")
        changed = _job(description="Build APIs, event pipelines, and internal platform tooling for customers.")

        first = compute_content_fingerprint(original)
        second = compute_content_fingerprint(original)
        third = compute_content_fingerprint(changed)

        self.assertEqual(first, second)
        self.assertNotEqual(first, third)

    def test_staleness_marks_reposted_old_listing(self):
        existing = SimpleNamespace(
            first_published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            published_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
            content_fingerprint=compute_content_fingerprint(_job()),
            last_content_change_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            repost_count=1,
        )
        incoming = _job(published_at=datetime(2026, 4, 13, tzinfo=timezone.utc))
        result = _evaluate_staleness(
            existing,
            incoming,
            link_health={"provider_url_status": "good", "apply_url_status": "good"},
            reference_time=datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(result["staleness_status"], "suspect_reposted")
        self.assertIn("suspect_reposted", result["staleness_flags"])
        self.assertEqual(result["repost_count"], 2)

    def test_staleness_clears_when_content_changes(self):
        existing = SimpleNamespace(
            first_published_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
            published_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            content_fingerprint=compute_content_fingerprint(_job()),
            last_content_change_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            repost_count=3,
        )
        incoming = _job(
            description="Build backend APIs, workflow automation, platform tooling, and internal observability services for customers.",
            published_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        )
        result = _evaluate_staleness(
            existing,
            incoming,
            link_health={"provider_url_status": "good", "apply_url_status": "good"},
            reference_time=datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(result["staleness_status"], "fresh")
        self.assertEqual(result["last_content_change_at"], datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc))

    def test_build_job_payload_rejects_bad_provider_url_and_keeps_apply_metadata(self):
        rejected = _build_job_payload(
            _job(),
            existing=None,
            link_health={
                "provider_url_status": "bad",
                "provider_url_checked_at": datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc),
                "provider_url_error": None,
                "apply_url": None,
                "apply_host": None,
                "apply_portal": "missing",
                "apply_url_status": "missing",
                "apply_url_checked_at": None,
                "apply_url_error": None,
                "source_tags": ["provider:the_muse"],
                "flags": ["provider_url_bad"],
            },
            reference_time=datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc),
        )
        stored = _build_job_payload(
            _job(description="Build backend APIs and data services for internal and external customers with clear documentation and operational rigor."), 
            existing=None,
            link_health={
                "provider_url_status": "good",
                "provider_url_checked_at": datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc),
                "provider_url_error": None,
                "apply_url": "https://jobs.ashbyhq.com/acme/123",
                "apply_host": "jobs.ashbyhq.com",
                "apply_portal": "ashby",
                "apply_url_status": "good",
                "apply_url_checked_at": datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc),
                "apply_url_error": None,
                "source_tags": ["provider:the_muse", "apply_portal:ashby"],
                "flags": [],
            },
            reference_time=datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc),
        )

        self.assertFalse(rejected["should_store"])
        self.assertTrue(stored["should_store"])
        self.assertEqual(stored["payload"]["apply_portal"], "ashby")
        self.assertIn("apply_portal:ashby", stored["payload"]["source_tags"])
        self.assertEqual(
            stored["payload"]["dedup_hash"],
            compute_dedup_hash("Software Engineer", "Acme"),
        )

    def test_backfill_and_stale_audit_guards(self):
        now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
        row = SimpleNamespace(
            provider_url_checked_at=None,
            source_tags=[],
            apply_url=None,
            apply_url_checked_at=None,
            apply_portal="missing",
            first_published_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
            published_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
            staleness_checked_at=now - timedelta(days=2),
        )

        self.assertTrue(needs_link_health_backfill(row, reference_time=now))
        self.assertTrue(needs_stale_audit(row, reference_time=now))


if __name__ == "__main__":
    unittest.main()
