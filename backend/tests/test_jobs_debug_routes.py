from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import HTTPException

from app.api import deps as deps_api
from app.api import jobs as jobs_api
from app.schemas.job import NormalizedJob


class JobsDebugRouteTests(unittest.TestCase):
    def test_require_admin_or_developer_allows_admin(self):
        user = SimpleNamespace(is_admin=True, is_developer=False)
        resolved = deps_api.require_admin_or_developer(current_user=user)
        self.assertIs(resolved, user)

    def test_require_admin_or_developer_allows_developer(self):
        user = SimpleNamespace(is_admin=False, is_developer=True)
        resolved = deps_api.require_admin_or_developer(current_user=user)
        self.assertIs(resolved, user)

    def test_require_admin_or_developer_blocks_standard_user(self):
        user = SimpleNamespace(is_admin=False, is_developer=False)
        with self.assertRaises(HTTPException) as blocked:
            deps_api.require_admin_or_developer(current_user=user)
        self.assertEqual(blocked.exception.status_code, 403)

    def test_job_debug_overview_returns_service_payload(self):
        payload = {"providers": {"statuses": []}, "database": {"counts": {}}, "recent_syncs": [], "quota_usage": []}
        with patch.object(jobs_api, "build_job_board_overview", return_value=payload) as build_mock:
            response = jobs_api.job_debug_overview(db=object(), current_user=SimpleNamespace(is_admin=True))

        self.assertEqual(response, payload)
        build_mock.assert_called_once()

    def test_job_debug_db_insights_returns_service_payload(self):
        payload = {"summary": {}, "recent_syncs": [], "recent_inserts": []}
        with patch.object(jobs_api, "build_job_board_db_insights", return_value=payload) as build_mock:
            response = jobs_api.job_debug_db_insights(db=object(), current_user=SimpleNamespace(is_developer=True))

        self.assertEqual(response, payload)
        build_mock.assert_called_once()

    def test_probe_provider_success(self):
        adapter = Mock()
        adapter.fetch.return_value = [
            NormalizedJob(
                provider="the_muse",
                provider_job_id="123",
                provider_url="https://example.com/job/123",
                apply_url="https://example.com/apply/123",
                title="Software Engineer",
                company="Acme",
                location="Huntsville, AL",
                is_remote=True,
                categories=["Software Engineer"],
            )
        ]

        with patch.object(jobs_api, "get_adapter", return_value=adapter):
            response = jobs_api.probe_provider(
                request=jobs_api.ProviderProbeRequest(provider="the_muse", params={"page": 1}),
                current_user=SimpleNamespace(is_developer=True),
            )

        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["provider"], "the_muse")
        self.assertEqual(response["item_count"], 1)
        self.assertEqual(response["sample"][0]["title"], "Software Engineer")

    def test_probe_provider_invalid_provider_raises_http_400(self):
        with patch.object(jobs_api, "get_adapter", side_effect=ValueError("Unsupported job provider 'nope'")):
            with self.assertRaises(HTTPException) as error:
                jobs_api.probe_provider(
                    request=jobs_api.ProviderProbeRequest(provider="nope", params={}),
                    current_user=SimpleNamespace(is_admin=True),
                )

        self.assertEqual(error.exception.status_code, 400)

    def test_probe_provider_error_returns_error_payload(self):
        adapter = Mock()
        adapter.fetch.side_effect = RuntimeError("provider offline")

        with patch.object(jobs_api, "get_adapter", return_value=adapter):
            response = jobs_api.probe_provider(
                request=jobs_api.ProviderProbeRequest(provider="the_muse", params={"page": 1}),
                current_user=SimpleNamespace(is_developer=True),
            )

        self.assertEqual(response["status"], "error")
        self.assertEqual(response["error_message"], "provider offline")

    def test_probe_local_search_returns_preview_payload(self):
        payload = {
            "jobs": [{"id": 1, "name": "Engineer"}, {"id": 2, "name": "Designer"}],
            "total_jobs": 2,
            "total_pages": 1,
            "has_next_page": False,
        }
        with patch.object(jobs_api, "search_local_jobs", return_value=payload):
            response = jobs_api.probe_local_search(
                request=jobs_api.SearchProbeRequest(params={"page": 1, "page_size": 5, "category": ["tech"]}),
                db=object(),
                current_user=SimpleNamespace(is_developer=True),
            )

        self.assertEqual(response["status"], "ok")
        self.assertIn("payload_hash", response)
        self.assertEqual(response["response_preview"]["jobs"][0]["name"], "Engineer")

    def test_probe_live_search_returns_preview_payload(self):
        async def _run_test():
            payload = {
                "jobs": [{"id": 11, "name": "Sales Lead"}],
                "total_jobs": 1,
                "total_pages": 1,
                "has_next_page": False,
            }
            with patch("app.api.routes.search_jobs", new=AsyncMock(return_value=payload)):
                response = await jobs_api.probe_live_search(
                    request=jobs_api.SearchProbeRequest(params={"page": 1, "category": ["sales"]}),
                    db=object(),
                    current_user=SimpleNamespace(is_developer=True),
                )

            self.assertEqual(response["status"], "ok")
            self.assertIn("payload_hash", response)
            self.assertEqual(response["response_preview"]["jobs"][0]["name"], "Sales Lead")

        asyncio.run(_run_test())


if __name__ == "__main__":
    unittest.main()
