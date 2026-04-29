from __future__ import annotations

import io
import unittest
import zipfile

from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import account as account_api
from app.core.security import hash_password
from app.db.base import Base
from app.models.applicant_profile import ApplicantProfile
from app.models.apply_session import ApplySession, ApplySessionEvent, TrackedApplication
from app.models.parse_job import ParseJob
from app.models.resume import Resume
from app.models.user import GmailFeedback, GmailNotificationState, GmailSuppression, SavedJob, User
from app.services.user_data_export import build_user_data_export_zip


def _build_request(session: dict | None = None) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/account/export/reauth",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    if session is not None:
        scope["session"] = session
    return Request(scope)


class AccountDataExportTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(
            bind=engine,
            tables=[
                User.__table__,
                SavedJob.__table__,
                GmailSuppression.__table__,
                GmailNotificationState.__table__,
                GmailFeedback.__table__,
                Resume.__table__,
                ParseJob.__table__,
                ApplicantProfile.__table__,
                ApplySession.__table__,
                ApplySessionEvent.__table__,
                TrackedApplication.__table__,
            ],
        )
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    def _create_user(self, **overrides) -> User:
        user = User(
            email=overrides.pop("email", "export@example.com"),
            username=overrides.pop("username", "export@example.com"),
            hashed_password=overrides.pop("hashed_password", hash_password("Password123!")),
            email_verified=True,
            is_active=True,
            **overrides,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_export_requires_recent_reauth(self):
        user = self._create_user()
        request = _build_request(session={})
        with self.assertRaises(HTTPException) as export_error:
            account_api.export_my_data(request=request, db=self.db, current_user=user)
        self.assertEqual(export_error.exception.status_code, 401)

    def test_password_reauth_allows_zip_export(self):
        user = self._create_user()
        self.db.add(SavedJob(user_id=user.id, title="Software Engineer", company="UAH", url="https://example.com/jobs/1"))
        self.db.add(Resume(user_id=user.id, file_name="resume.pdf", raw_markdown="# Resume"))
        self.db.commit()

        session = {}
        request = _build_request(session=session)
        response = account_api.export_reauth(
            payload=account_api.ExportReauthRequest(method="password", password="Password123!"),
            request=request,
            db=self.db,
            current_user=user,
        )
        self.assertEqual(response.message, "Re-authenticated for data export")
        self.assertGreater(int(session.get("export_reauth_until", 0)), 0)

        archive = build_user_data_export_zip(db=self.db, user=user)
        with zipfile.ZipFile(io.BytesIO(archive), "r") as zipped:
            names = set(zipped.namelist())
        self.assertIn("account_profile.csv", names)
        self.assertIn("saved_jobs.csv", names)
        self.assertIn("resumes.csv", names)

