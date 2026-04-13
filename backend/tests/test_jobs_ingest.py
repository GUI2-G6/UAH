from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import IntegrityError

import app.services.ingest as ingest_module
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
    upsert_job,
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


_DEFAULT_REFERENCE_TIME = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
_USE_COMPUTED_HASH = object()


def _payload(
    job: NormalizedJob,
    *,
    existing=None,
    reference_time: datetime = _DEFAULT_REFERENCE_TIME,
    dedup_hash=_USE_COMPUTED_HASH,
    is_active: bool = True,
) -> dict:
    effective_dedup_hash = dedup_hash
    if effective_dedup_hash is _USE_COMPUTED_HASH:
        effective_dedup_hash = compute_dedup_hash(job.title, job.company)
    return {
        "id": getattr(existing, "id", None) or "job-row-id",
        "provider": job.provider,
        "provider_job_id": job.provider_job_id,
        "provider_url": job.provider_url,
        "provider_url_status": "good",
        "provider_url_checked_at": reference_time,
        "provider_url_error": None,
        "apply_url": "https://jobs.example.com/apply/123",
        "apply_host": "jobs.example.com",
        "apply_portal": "ashby",
        "apply_url_status": "good",
        "apply_url_checked_at": reference_time,
        "apply_url_error": None,
        "source_tags": [f"provider:{job.provider}", "apply_portal:ashby"],
        "title": job.title,
        "company": job.company,
        "company_url": job.company_url,
        "location": job.location,
        "is_remote": bool(job.is_remote),
        "job_type": job.job_type,
        "experience_level": job.experience_level,
        "categories": list(job.categories),
        "description": job.description,
        "short_description": "Short description",
        "quality_score": 0.92,
        "quality_flags": [],
        "consecutive_misses": 0,
        "first_seen_at": getattr(existing, "first_seen_at", None) or reference_time,
        "last_seen_at": reference_time,
        "published_at": job.published_at,
        "first_published_at": job.published_at,
        "content_fingerprint": "content-fingerprint",
        "last_content_change_at": reference_time,
        "is_active": is_active,
        "is_featured": getattr(existing, "is_featured", False),
        "display_tier": "active" if is_active else "hidden",
        "staleness_status": "fresh",
        "staleness_flags": [],
        "staleness_checked_at": reference_time,
        "repost_count": int(getattr(existing, "repost_count", 0) or 0),
        "dedup_hash": effective_dedup_hash,
    }


class _FakeInsertStatement:
    def __init__(self, payload: dict):
        self.payload = dict(payload)
        self.index_elements = None
        self.set_values = None

    def on_conflict_do_update(self, *, index_elements, set_):
        self.index_elements = list(index_elements)
        self.set_values = dict(set_)
        return self


class _FakeInsertBuilder:
    def values(self, **payload):
        return _FakeInsertStatement(payload)


def _fake_insert(_model):
    return _FakeInsertBuilder()


def _query_with_result(result):
    query = MagicMock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.first.return_value = result
    return query


def _dedup_hash_integrity_error() -> IntegrityError:
    class _Orig(Exception):
        def __init__(self):
            self.diag = SimpleNamespace(constraint_name="idx_jobs_dedup_hash")
            super().__init__('duplicate key value violates unique constraint "idx_jobs_dedup_hash"')

    return IntegrityError("INSERT", {}, _Orig())


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

    @patch.object(ingest_module, "insert", side_effect=_fake_insert)
    @patch.object(ingest_module, "_build_job_payload")
    @patch.object(ingest_module, "_evaluate_job_link_health", return_value={"provider_url_status": "good"})
    @patch.object(ingest_module, "get_provider_controls", return_value=SimpleNamespace(ingest_enabled=True))
    def test_upsert_same_provider_collision_nulls_hash_and_increments_canonical(
        self,
        _controls,
        _link_health,
        build_payload,
        _insert,
    ):
        job = _job(provider_job_id="21463732")
        owner = SimpleNamespace(
            id="owner-row",
            provider=job.provider,
            provider_job_id="17669155",
            repost_count=2,
        )
        build_payload.return_value = {"should_store": True, "payload": _payload(job)}

        existing_query = _query_with_result(None)
        owner_query = _query_with_result(owner)
        db = MagicMock()
        db.query.side_effect = [existing_query, owner_query]

        with patch.object(ingest_module.settings, "JOB_DEDUP_ENABLED", True):
            state, created = upsert_job(job, db_session=db, provider_adapter=object())

        self.assertEqual(state, "inserted")
        self.assertTrue(created)
        self.assertEqual(owner.repost_count, 3)
        self.assertEqual(db.execute.call_count, 1)
        statement = db.execute.call_args.args[0]
        self.assertIsNone(statement.payload["dedup_hash"])
        self.assertIsNone(statement.set_values["dedup_hash"])
        db.rollback.assert_not_called()
        db.commit.assert_called_once()

    @patch.object(ingest_module, "insert", side_effect=_fake_insert)
    @patch.object(ingest_module, "_build_job_payload")
    @patch.object(ingest_module, "_evaluate_job_link_health", return_value={"provider_url_status": "good"})
    @patch.object(ingest_module, "get_provider_controls", return_value=SimpleNamespace(ingest_enabled=True))
    def test_upsert_same_provider_duplicate_repeat_sync_does_not_reincrement_canonical(
        self,
        _controls,
        _link_health,
        build_payload,
        _insert,
    ):
        existing = SimpleNamespace(
            id="duplicate-row",
            dedup_hash=None,
            repost_count=0,
            first_seen_at=_DEFAULT_REFERENCE_TIME,
        )
        owner = SimpleNamespace(
            id="owner-row",
            provider="the_muse",
            provider_job_id="17669155",
            repost_count=5,
        )
        job = _job(provider_job_id="21463732")
        build_payload.return_value = {"should_store": True, "payload": _payload(job, existing=existing)}

        existing_query = _query_with_result(existing)
        owner_query = _query_with_result(owner)
        db = MagicMock()
        db.query.side_effect = [existing_query, owner_query]

        with patch.object(ingest_module.settings, "JOB_DEDUP_ENABLED", True):
            state, created = upsert_job(job, db_session=db, provider_adapter=object())

        self.assertEqual(state, "updated")
        self.assertFalse(created)
        self.assertEqual(owner.repost_count, 5)
        statement = db.execute.call_args.args[0]
        self.assertIsNone(statement.payload["dedup_hash"])
        self.assertIsNone(statement.set_values["dedup_hash"])
        db.commit.assert_called_once()

    @patch.object(ingest_module, "_build_job_payload")
    @patch.object(ingest_module, "_evaluate_job_link_health", return_value={"provider_url_status": "good"})
    @patch.object(ingest_module, "get_provider_controls", return_value=SimpleNamespace(ingest_enabled=True))
    def test_upsert_cross_provider_duplicate_keeps_existing_short_circuit_behavior(
        self,
        _controls,
        _link_health,
        build_payload,
    ):
        job = _job(provider="the_muse", provider_job_id="21463732")
        existing = SimpleNamespace(
            id="existing-row",
            dedup_hash=compute_dedup_hash(job.title, job.company),
            is_active=True,
            display_tier="active",
            last_seen_at=None,
            consecutive_misses=4,
        )
        owner = SimpleNamespace(
            id="owner-row",
            provider="findwork",
            provider_job_id="17669155",
            repost_count=2,
            is_active=True,
            display_tier="stale",
            last_seen_at=None,
            consecutive_misses=3,
            source_tags=["provider:findwork"],
        )
        build_payload.return_value = {"should_store": True, "payload": _payload(job, existing=existing)}

        existing_query = _query_with_result(existing)
        owner_query = _query_with_result(owner)
        db = MagicMock()
        db.query.side_effect = [existing_query, owner_query]

        with patch.object(ingest_module.settings, "JOB_DEDUP_ENABLED", True):
            state, created = upsert_job(job, db_session=db, provider_adapter=object())

        self.assertEqual(state, "duplicate")
        self.assertFalse(created)
        self.assertFalse(existing.is_active)
        self.assertIsNone(existing.dedup_hash)
        self.assertIn("duplicate_provider:the_muse", owner.source_tags)
        db.execute.assert_not_called()
        db.commit.assert_called_once()

    @patch.object(ingest_module, "insert", side_effect=_fake_insert)
    @patch.object(ingest_module, "_build_job_payload")
    @patch.object(ingest_module, "_evaluate_job_link_health", return_value={"provider_url_status": "good"})
    @patch.object(ingest_module, "get_provider_controls", return_value=SimpleNamespace(ingest_enabled=True))
    def test_upsert_inactive_duplicate_reactivation_does_not_reclaim_hash(
        self,
        _controls,
        _link_health,
        build_payload,
        _insert,
    ):
        job = _job(provider_job_id="21463732")
        dedup_hash = compute_dedup_hash(job.title, job.company)
        existing = SimpleNamespace(
            id="inactive-duplicate-row",
            dedup_hash=dedup_hash,
            repost_count=1,
            first_seen_at=_DEFAULT_REFERENCE_TIME,
            is_active=False,
        )
        owner = SimpleNamespace(
            id="owner-row",
            provider=job.provider,
            provider_job_id="17669155",
            repost_count=7,
        )
        build_payload.return_value = {
            "should_store": True,
            "payload": _payload(job, existing=existing, dedup_hash=dedup_hash, is_active=True),
        }

        existing_query = _query_with_result(existing)
        owner_query = _query_with_result(owner)
        db = MagicMock()
        db.query.side_effect = [existing_query, owner_query]

        with patch.object(ingest_module.settings, "JOB_DEDUP_ENABLED", True):
            state, created = upsert_job(job, db_session=db, provider_adapter=object())

        self.assertEqual(state, "updated")
        self.assertFalse(created)
        self.assertEqual(owner.repost_count, 8)
        statement = db.execute.call_args.args[0]
        self.assertTrue(statement.set_values["is_active"])
        self.assertIsNone(statement.payload["dedup_hash"])
        self.assertIsNone(statement.set_values["dedup_hash"])
        db.commit.assert_called_once()

    @patch.object(ingest_module, "insert", side_effect=_fake_insert)
    @patch.object(ingest_module, "_build_job_payload")
    @patch.object(ingest_module, "_evaluate_job_link_health", return_value={"provider_url_status": "good"})
    @patch.object(ingest_module, "get_provider_controls", return_value=SimpleNamespace(ingest_enabled=True))
    def test_upsert_retries_once_with_null_hash_after_dedup_constraint_error(
        self,
        _controls,
        _link_health,
        build_payload,
        _insert,
    ):
        job = _job(provider_job_id="21463732")
        build_payload.return_value = {"should_store": True, "payload": _payload(job)}

        existing_query = _query_with_result(None)
        owner_query = _query_with_result(None)
        db = MagicMock()
        db.query.side_effect = [existing_query, owner_query]
        db.execute.side_effect = [_dedup_hash_integrity_error(), None]

        with patch.object(ingest_module.settings, "JOB_DEDUP_ENABLED", True):
            state, created = upsert_job(job, db_session=db, provider_adapter=object())

        self.assertEqual(state, "inserted")
        self.assertTrue(created)
        self.assertEqual(db.execute.call_count, 2)
        first_statement = db.execute.call_args_list[0].args[0]
        second_statement = db.execute.call_args_list[1].args[0]
        self.assertIsNotNone(first_statement.payload["dedup_hash"])
        self.assertIsNone(second_statement.payload["dedup_hash"])
        self.assertIsNone(second_statement.set_values["dedup_hash"])
        db.rollback.assert_called_once()
        db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
