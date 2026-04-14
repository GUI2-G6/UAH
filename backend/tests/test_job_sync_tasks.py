from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

redis_stub = types.ModuleType("redis")


class _RedisError(Exception):
    pass


class _RedisClient:
    @classmethod
    def from_url(cls, *_args, **_kwargs):
        return cls()

    def ping(self):
        return True

    def set(self, *_args, **_kwargs):
        return True

    def delete(self, *_args, **_kwargs):
        return 1

    def exists(self, *_args, **_kwargs):
        return 0


redis_stub.Redis = _RedisClient
redis_stub.RedisError = _RedisError
sys.modules.setdefault("redis", redis_stub)

celery_stub = types.ModuleType("celery")


class _CeleryConf:
    def update(self, **_kwargs):
        return None


class _TaskWrapper:
    def __init__(self, func):
        self.run = func

    def delay(self, *_args, **_kwargs):
        return None


class _CeleryApp:
    def __init__(self, *_args, **_kwargs):
        self.conf = _CeleryConf()

    def task(self, *args, **kwargs):
        def decorator(func):
            return _TaskWrapper(func)

        return decorator


celery_stub.Celery = _CeleryApp
sys.modules.setdefault("celery", celery_stub)

import app.tasks.job_sync as job_sync


class JobSyncTaskTests(unittest.TestCase):
    @patch.object(job_sync, "_release_lock")
    @patch.object(job_sync, "backfill_job_dedup_hash_batch")
    @patch.object(job_sync, "_acquire_lock", return_value=True)
    def test_dedup_backfill_task_runs_batch(self, acquire_lock, batch_helper, release_lock):
        batch_helper.return_value = {
            "scanned": 25,
            "hashed": 18,
            "deactivated": 6,
            "skipped": 1,
        }

        with patch.object(job_sync.settings, "JOB_SYNC_LOCK_TTL_SECONDS", 900):
            result = job_sync.backfill_job_dedup_hashes.run(None)

        acquire_lock.assert_called_once()
        batch_helper.assert_called_once_with()
        release_lock.assert_called_once()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["hashed"], 18)
        self.assertEqual(result["deactivated"], 6)

    @patch.object(job_sync, "_acquire_lock", return_value=False)
    def test_dedup_backfill_task_skips_when_locked(self, acquire_lock):
        with patch.object(job_sync.settings, "JOB_SYNC_LOCK_TTL_SECONDS", 900):
            result = job_sync.backfill_job_dedup_hashes.run(None)

        acquire_lock.assert_called_once()
        self.assertEqual(result, {"status": "skipped_locked"})

    @patch.object(job_sync, "_release_lock")
    @patch.object(job_sync, "backfill_job_country_normalization_batch")
    @patch.object(job_sync, "_acquire_lock", return_value=True)
    def test_country_backfill_task_runs_batch_with_scope(self, acquire_lock, batch_helper, release_lock):
        batch_helper.return_value = {
            "scanned": 12,
            "updated": 9,
            "changed_country_code": 7,
            "changed_country_name_only": 2,
            "unchanged": 2,
            "xx_remaining": 1,
            "xu_remaining": 0,
            "batches_committed": 1,
        }

        with patch.object(job_sync.settings, "JOB_SYNC_LOCK_TTL_SECONDS", 900):
            result = job_sync.backfill_job_country_normalization.run(None, scope="repair")

        acquire_lock.assert_called_once()
        batch_helper.assert_called_once_with(scope="repair")
        release_lock.assert_called_once()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["scope"], "repair")
        self.assertEqual(result["updated"], 9)

    @patch.object(job_sync, "_acquire_lock", return_value=False)
    def test_country_backfill_task_skips_when_locked(self, acquire_lock):
        with patch.object(job_sync.settings, "JOB_SYNC_LOCK_TTL_SECONDS", 900):
            result = job_sync.backfill_job_country_normalization.run(None)

        acquire_lock.assert_called_once()
        self.assertEqual(result, {"status": "skipped_locked", "scope": "all"})


if __name__ == "__main__":
    unittest.main()
