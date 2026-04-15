from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from app.services import parse_job_runner, parse_queue


class _FakeSession:
    def __init__(self, job, resume):
        self._job = job
        self._resume = resume
        self._active_model = None
        self._parse_job_first_calls = 0
        self.commits = 0

    def query(self, model):
        self._active_model = model
        return self

    def filter(self, *args, **kwargs):
        return self

    def with_for_update(self, **kwargs):
        return self

    def first(self):
        if self._active_model is parse_job_runner.ParseJob:
            self._parse_job_first_calls += 1
            if self._parse_job_first_calls == 1:
                return self._job
            return None
        if self._active_model is parse_job_runner.Resume:
            return self._resume
        return None

    def commit(self):
        self.commits += 1

    def refresh(self, _obj):
        return None

    def close(self):
        return None


class ParseQueueIsolationTests(unittest.IsolatedAsyncioTestCase):
    def test_retry_policies_are_method_specific(self):
        with patch.object(parse_queue.settings, "PARSE_QUEUE_MAX_RETRIES", 3), \
             patch.object(parse_queue.settings, "PARSE_QUEUE_MAX_RETRIES_CLOUD", -1), \
             patch.object(parse_queue.settings, "PARSE_QUEUE_MAX_RETRIES_LOCAL", 2), \
             patch.object(parse_queue.settings, "PARSE_QUEUE_MAX_RETRIES_RULES", 0):
            self.assertEqual(parse_queue._max_retries_for_method("cloud"), 3)
            self.assertEqual(parse_queue._max_retries_for_method("local"), 2)
            self.assertEqual(parse_queue._max_retries_for_method("rules"), 0)

    def test_retry_backoff_is_method_specific(self):
        self.assertEqual(parse_queue._retry_delay_seconds("cloud", 2), 4)
        self.assertEqual(parse_queue._retry_delay_seconds("local", 2), 4)
        self.assertEqual(parse_queue._retry_delay_seconds("rules", 2), 0)

    def test_cloud_retry_only_happens_for_retryable_cloud_codes(self):
        self.assertTrue(parse_queue._can_retry_job("cloud", "CLOUD_LLM_RATE_LIMITED"))
        self.assertFalse(parse_queue._can_retry_job("cloud", "CLOUD_LLM_QUOTA_EXHAUSTED"))
        self.assertTrue(parse_queue._can_retry_job("local", "LLM_TIMEOUT"))

    def test_cloud_min_interval_is_configurable(self):
        with patch.object(parse_queue.settings, "PARSE_QUEUE_CLOUD_MIN_INTERVAL_SECONDS", 7):
            self.assertEqual(parse_queue._min_interval_for_method("cloud"), 7)
            self.assertEqual(parse_queue._min_interval_for_method("local"), 0)

    async def test_run_parse_job_fails_on_resume_owner_mismatch(self):
        job = SimpleNamespace(
            id=1,
            status="queued",
            resume_id=11,
            user_id=100,
            method="local",
            error_code=None,
            error_message=None,
            progress_stage=None,
            result_summary=None,
        )
        resume = SimpleNamespace(id=11, user_id=200, pdf_data=b"pdf")
        fake_db = _FakeSession(job=job, resume=resume)

        with patch.object(parse_job_runner, "SessionLocal", return_value=fake_db):
            ok = await parse_job_runner.run_parse_job(1)

        self.assertFalse(ok)
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.error_code, "RESUME_OWNERSHIP_MISMATCH")
        self.assertGreaterEqual(fake_db.commits, 1)

    async def test_run_parse_job_sets_pending_review_draft_on_success(self):
        structured = {
            "personal_info": {"first_name": "Local", "last_name": "Developer", "email": "local@example.com"},
            "skills": {"technical": ["Vue"]},
            "_validation": {
                "portal_ready": True,
                "has_name": True,
                "has_email": True,
                "education_count": 1,
                "experience_count": 1,
                "skills_count": 1,
                "missing_required": [],
            },
        }
        job = SimpleNamespace(
            id=2,
            status="queued",
            resume_id=12,
            user_id=200,
            method="local",
            error_code=None,
            error_message=None,
            progress_stage=None,
            result_summary=None,
        )
        resume = SimpleNamespace(
            id=12,
            user_id=200,
            pdf_data=b"pdf",
            raw_markdown=None,
            raw_markdown_source=None,
            raw_markdown_method=None,
            raw_markdown_updated_at=None,
            structured_data=None,
            parse_method=None,
            portal_ready=False,
            review_status=None,
            review_draft=None,
            review_updated_at=None,
        )
        fake_db = _FakeSession(job=job, resume=resume)

        with patch.object(parse_job_runner, "SessionLocal", return_value=fake_db), \
             patch.object(parse_job_runner, "get_parse_input_text", AsyncMock(return_value={"ok": True, "text": "resume markdown"})), \
             patch.object(parse_job_runner, "parse_markdown_by_method", AsyncMock(return_value={"parsed": "ignored"})), \
             patch.object(parse_job_runner, "validate_and_fix", return_value=structured):
            ok = await parse_job_runner.run_parse_job(2)

        self.assertTrue(ok)
        self.assertEqual(job.status, "success")
        self.assertEqual(resume.parse_method, "local")
        self.assertEqual(resume.raw_markdown, "resume markdown")
        self.assertEqual(resume.raw_markdown_source, "local_ocr")
        self.assertEqual(resume.raw_markdown_method, "local")
        self.assertIsNotNone(resume.raw_markdown_updated_at)
        self.assertTrue(resume.portal_ready)
        self.assertEqual(resume.review_status, "pending")
        self.assertEqual(resume.review_draft, structured)
        self.assertIsNotNone(resume.review_updated_at)
        self.assertEqual(job.result_summary["portal_ready"], True)
        self.assertEqual(job.result_summary["skills_count"], 1)


if __name__ == "__main__":
    unittest.main()
