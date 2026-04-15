from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api import routes as routes_api
from app.models.job import Job
from app.models.user import SavedJob
from app.schemas.user import SaveJobRequest


def _utc(hours_ago: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours_ago)


def _saved_job(**overrides):
    job = SavedJob(
        id=overrides.get("id"),
        user_id=overrides.get("user_id", 1),
        job_id=overrides.get("job_id"),
        provider=overrides.get("provider"),
        provider_job_id=overrides.get("provider_job_id"),
        title=overrides.get("title", "Saved Role"),
        company=overrides.get("company", "Saved Co"),
        url=overrides.get("url", "https://example.com/job"),
    )
    job.created_at = overrides.get("created_at", _utc(0))
    return job


class _FakeQuery:
    def __init__(self, model, rows):
        self.model = model
        self.rows = list(rows)

    def filter(self, *conditions):
        filtered = self.rows
        for condition in conditions:
            filtered = [row for row in filtered if _matches_condition(row, condition)]
        return _FakeQuery(self.model, filtered)

    def order_by(self, *_args):
        if self.model is SavedJob:
            ordered = sorted(
                self.rows,
                key=lambda row: (
                    getattr(row, "created_at", datetime.min.replace(tzinfo=timezone.utc)),
                    getattr(row, "id", 0),
                ),
                reverse=True,
            )
            return _FakeQuery(self.model, ordered)
        return self

    def count(self):
        return len(self.rows)

    def offset(self, amount):
        return _FakeQuery(self.model, self.rows[int(amount or 0):])

    def limit(self, amount):
        return _FakeQuery(self.model, self.rows[: int(amount or 0)])

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


def _matches_condition(row, condition):
    if hasattr(condition, "clauses"):
        return all(_matches_condition(row, clause) for clause in condition.clauses)

    left_name = getattr(getattr(condition, "left", None), "name", "")
    right_value = getattr(getattr(condition, "right", None), "value", None)
    operator_name = getattr(getattr(condition, "operator", None), "__name__", "")

    if operator_name == "eq":
        return getattr(row, left_name, None) == right_value

    return True


class _FakeDb:
    def __init__(self, saved_jobs=None, jobs=None):
        self.saved_jobs = list(saved_jobs or [])
        self.jobs = list(jobs or [])
        self.pending_saved_jobs = []
        self.next_saved_id = max([job.id for job in self.saved_jobs] or [0]) + 1

    def query(self, model):
        if model is SavedJob:
            return _FakeQuery(model, self.saved_jobs)
        if model is Job:
            return _FakeQuery(model, self.jobs)
        return _FakeQuery(model, [])

    def add(self, obj):
        if isinstance(obj, SavedJob):
            if obj.id is None:
                obj.id = self.next_saved_id
                self.next_saved_id += 1
            if getattr(obj, "created_at", None) is None:
                obj.created_at = datetime.now(timezone.utc)
            self.pending_saved_jobs.append(obj)

    def commit(self):
        if self.pending_saved_jobs:
            self.saved_jobs.extend(self.pending_saved_jobs)
            self.pending_saved_jobs = []
        return None

    def rollback(self):
        self.pending_saved_jobs = []

    def refresh(self, _obj):
        return None

    def delete(self, obj):
        self.saved_jobs = [job for job in self.saved_jobs if job.id != obj.id]


class _CommitIntegrityFailureDb(_FakeDb):
    def __init__(self, race_saved_job=None, **kwargs):
        super().__init__(**kwargs)
        self.race_saved_job = race_saved_job

    def commit(self):
        if self.race_saved_job is not None:
            self.saved_jobs.append(self.race_saved_job)
        raise IntegrityError("insert into saved_jobs", {}, Exception("duplicate key value violates unique constraint"))


class _CommitFailureDb(_FakeDb):
    def commit(self):
        raise SQLAlchemyError("database unavailable")


class SavedJobsRouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_job_accepts_string_provider_job_id(self):
        db = _FakeDb()
        current_user = type("User", (), {"id": 1})()

        response = await routes_api.save_job(
            SaveJobRequest(
                provider="arbeitnow",
                provider_job_id="backend-python-engineer",
                name="Backend Python Engineer",
                company="North Ridge",
                url="https://example.com/backend-python-engineer",
            ),
            db=db,
            current_user=current_user,
        )

        self.assertEqual(response["saved_job_id"], 1)
        self.assertEqual(db.saved_jobs[0].provider, "arbeitnow")
        self.assertEqual(db.saved_jobs[0].provider_job_id, "backend-python-engineer")
        self.assertIsNone(db.saved_jobs[0].job_id)

    async def test_save_job_blocks_duplicate_for_same_provider_and_provider_job_id(self):
        db = _FakeDb(saved_jobs=[_saved_job(id=1, provider="the_muse", provider_job_id="7619281")])
        current_user = type("User", (), {"id": 1})()

        with self.assertRaises(HTTPException) as exc:
            await routes_api.save_job(
                SaveJobRequest(
                    provider="the_muse",
                    provider_job_id="7619281",
                    name="Software Engineer",
                    company="Acme",
                    url="https://example.com/7619281",
                ),
                db=db,
                current_user=current_user,
            )

        self.assertEqual(exc.exception.status_code, 400)

    async def test_save_job_allows_same_provider_job_id_for_different_provider(self):
        db = _FakeDb(saved_jobs=[_saved_job(id=1, provider="the_muse", provider_job_id="7619281")])
        current_user = type("User", (), {"id": 1})()

        response = await routes_api.save_job(
            SaveJobRequest(
                provider="adzuna",
                provider_job_id="7619281",
                name="Software Engineer",
                company="Acme",
                url="https://example.com/adzuna-7619281",
            ),
            db=db,
            current_user=current_user,
        )

        self.assertEqual(response["saved_job_id"], 2)
        self.assertEqual(len(db.saved_jobs), 2)

    async def test_save_job_returns_duplicate_when_commit_hits_integrity_race(self):
        db = _CommitIntegrityFailureDb(
            race_saved_job=_saved_job(id=2, provider="the_muse", provider_job_id="7619281")
        )
        current_user = type("User", (), {"id": 1})()

        with self.assertRaises(HTTPException) as exc:
            await routes_api.save_job(
                SaveJobRequest(
                    provider="the_muse",
                    provider_job_id="7619281",
                    name="Software Engineer",
                    company="Acme",
                    url="https://example.com/7619281",
                ),
                db=db,
                current_user=current_user,
            )

        self.assertEqual(exc.exception.status_code, 400)

    async def test_save_job_returns_generic_500_for_non_duplicate_commit_failure(self):
        db = _CommitFailureDb()
        current_user = type("User", (), {"id": 1})()

        with self.assertRaises(HTTPException) as exc:
            await routes_api.save_job(
                SaveJobRequest(
                    provider="the_muse",
                    provider_job_id="7619281",
                    name="Software Engineer",
                    company="Acme",
                    url="https://example.com/7619281",
                ),
                db=db,
                current_user=current_user,
            )

        self.assertEqual(exc.exception.status_code, 500)
        self.assertEqual(exc.exception.detail, "Could not save job right now")

    async def test_get_saved_jobs_paginates_newest_first(self):
        db = _FakeDb(
            saved_jobs=[
                _saved_job(id=1, title="Oldest", created_at=_utc(10)),
                _saved_job(id=2, title="Middle", created_at=_utc(5)),
                _saved_job(id=3, title="Newest", created_at=_utc(1)),
            ]
        )
        current_user = type("User", (), {"id": 1})()

        payload = await routes_api.get_saved_jobs(page=1, page_size=2, db=db, current_user=current_user)

        self.assertEqual(payload["total_jobs"], 3)
        self.assertEqual(payload["total_pages"], 2)
        self.assertEqual([job["name"] for job in payload["saved_jobs"]], ["Newest", "Middle"])

    async def test_get_saved_jobs_falls_back_to_saved_snapshot_when_live_job_missing(self):
        db = _FakeDb(
            saved_jobs=[
                _saved_job(
                    id=4,
                    provider="the_muse",
                    provider_job_id="missing-role",
                    title="Snapshot Role",
                    company="Snapshot Co",
                    url="https://example.com/snapshot-role",
                )
            ]
        )
        current_user = type("User", (), {"id": 1})()

        payload = await routes_api.get_saved_jobs(page=1, page_size=10, db=db, current_user=current_user)
        saved = payload["saved_jobs"][0]

        self.assertEqual(saved["saved_job_id"], 4)
        self.assertEqual(saved["provider_job_id"], "missing-role")
        self.assertEqual(saved["name"], "Snapshot Role")
        self.assertEqual(saved["job_url"], "https://example.com/snapshot-role")

    async def test_unsave_job_removes_saved_record(self):
        db = _FakeDb(saved_jobs=[_saved_job(id=6, title="Delete Me")])
        current_user = type("User", (), {"id": 1})()

        payload = await routes_api.unsave_job(job_id=6, db=db, current_user=current_user)

        self.assertEqual(payload["message"], "Job removed from saved list")
        self.assertEqual(len(db.saved_jobs), 0)

    async def test_unsave_job_returns_not_found_for_missing_record(self):
        db = _FakeDb()
        current_user = type("User", (), {"id": 1})()

        with self.assertRaises(HTTPException) as exc:
            await routes_api.unsave_job(job_id=999, db=db, current_user=current_user)

        self.assertEqual(exc.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
