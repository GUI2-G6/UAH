from __future__ import annotations

from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import uuid

import httpx

from app.scrapers.checklist import PreScrapingChecklist as checklist


def _make_response(
    url: str,
    *,
    status_code: int = 200,
    text: str = "",
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        headers=headers,
        request=httpx.Request("GET", url),
        text=text,
    )


class _FakeChecklistClient:
    def __init__(self, responses: dict[str, httpx.Response | Exception]):
        self._responses = responses

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url: str) -> httpx.Response:
        value = self._responses.get(
            url,
            _make_response(url, status_code=404, text="not found", headers={"content-type": "text/html"}),
        )
        if isinstance(value, Exception):
            raise value
        return value


class PreScrapingChecklistTests(unittest.TestCase):
    def _run_with_responses(self, responses, *, opted_out: bool = False):
        temp_root = Path(__file__).resolve().parent / "_tmp_checklist_logs"
        temp_dir = temp_root / uuid.uuid4().hex
        temp_dir.mkdir(parents=True, exist_ok=False)
        self.addCleanup(shutil.rmtree, temp_root, True)
        with patch.object(
            checklist,
            "LOG_DIRECTORY",
            temp_dir,
        ), patch.object(
            checklist,
            "_build_client",
            return_value=_FakeChecklistClient(responses),
        ), patch.object(checklist, "check_opt_out", return_value=opted_out):
            return checklist.run_checklist("https://example.com")

    def test_approved_provider_generates_log_and_approved_verdict(self):
        responses = {
            "https://example.com/robots.txt": _make_response(
                "https://example.com/robots.txt",
                text="User-agent: *\nAllow: /\nCrawl-delay: 2\n",
            ),
            "https://example.com/terms": _make_response(
                "https://example.com/terms",
                text="<html><body><p>These terms cover normal site use and content access.</p></body></html>",
                headers={"content-type": "text/html"},
            ),
            "https://example.com": _make_response(
                "https://example.com",
                text="<html><body><h1>Jobs</h1><p>Browse open roles without JavaScript.</p></body></html>",
                headers={"content-type": "text/html"},
            ),
        }
        report = self._run_with_responses(responses)

        self.assertEqual(report["verdict"], "APPROVED")
        self.assertTrue(report["robots_txt"]["allowed"])
        self.assertTrue(Path(report["log_file"]).exists())

    def test_opted_out_provider_is_rejected(self):
        responses = {
            "https://example.com/robots.txt": _make_response(
                "https://example.com/robots.txt",
                text="User-agent: *\nAllow: /\n",
            ),
            "https://example.com/terms": _make_response(
                "https://example.com/terms",
                text="<html><body><p>Standard terms page.</p></body></html>",
                headers={"content-type": "text/html"},
            ),
            "https://example.com": _make_response(
                "https://example.com",
                text="<html><body><p>Jobs page.</p></body></html>",
                headers={"content-type": "text/html"},
            ),
        }
        report = self._run_with_responses(responses, opted_out=True)

        self.assertEqual(report["verdict"], "REJECTED")
        self.assertTrue(report["opt_out"]["is_opted_out"])

    def test_robots_blocked_provider_is_rejected(self):
        responses = {
            "https://example.com/robots.txt": _make_response(
                "https://example.com/robots.txt",
                text="User-agent: *\nDisallow: /\n",
            ),
            "https://example.com/terms": _make_response(
                "https://example.com/terms",
                text="<html><body><p>Standard terms page.</p></body></html>",
                headers={"content-type": "text/html"},
            ),
            "https://example.com": _make_response(
                "https://example.com",
                text="<html><body><p>Jobs page.</p></body></html>",
                headers={"content-type": "text/html"},
            ),
        }
        report = self._run_with_responses(responses)

        self.assertEqual(report["verdict"], "REJECTED")
        self.assertFalse(report["robots_txt"]["allowed"])

    def test_ambiguous_terms_language_requires_review(self):
        responses = {
            "https://example.com/robots.txt": _make_response(
                "https://example.com/robots.txt",
                text="User-agent: *\nAllow: /\n",
            ),
            "https://example.com/terms": _make_response(
                "https://example.com/terms",
                text="<html><body><p>Commercial use and reproduction may require separate permission.</p></body></html>",
                headers={"content-type": "text/html"},
            ),
            "https://example.com": _make_response(
                "https://example.com",
                text="<html><body><p>Jobs page.</p></body></html>",
                headers={"content-type": "text/html"},
            ),
        }
        report = self._run_with_responses(responses)

        self.assertEqual(report["verdict"], "NEEDS REVIEW")
        self.assertTrue(report["terms_of_service"]["scan"]["ambiguous_language"])

    def test_anti_bot_signals_require_review(self):
        responses = {
            "https://example.com/robots.txt": _make_response(
                "https://example.com/robots.txt",
                text="User-agent: *\nAllow: /\n",
            ),
            "https://example.com/terms": _make_response(
                "https://example.com/terms",
                text="<html><body><p>Standard terms page.</p></body></html>",
                headers={"content-type": "text/html"},
            ),
            "https://example.com": _make_response(
                "https://example.com",
                text="<html><body><p>Jobs page.</p></body></html>",
                headers={"content-type": "text/html", "cf-ray": "abc123"},
            ),
        }
        report = self._run_with_responses(responses)

        self.assertEqual(report["verdict"], "NEEDS REVIEW")
        self.assertIn("cloudflare", report["anti_bot"]["signals"])


if __name__ == "__main__":
    unittest.main()
