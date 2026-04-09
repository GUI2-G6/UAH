from types import SimpleNamespace
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
