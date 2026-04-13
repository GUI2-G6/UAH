from __future__ import annotations

import unittest

from app.services.job_link_health import (
    _JOB_URL_VALIDATION_CACHE,
    build_source_tags,
    classify_apply_portal,
    classify_job_url_validation_verdict,
    validate_job_link,
)


class _FakeResponse:
    def __init__(self, *, status_code=200, text="", url="https://example.com/jobs/role"):
        self.status_code = status_code
        self.text = text
        self.url = url


class _FakeClient:
    def __init__(self, response_by_url=None, raises_by_url=None):
        self.response_by_url = response_by_url or {}
        self.raises_by_url = raises_by_url or set()
        self.calls: list[str] = []

    def get(self, url):
        self.calls.append(url)
        if url in self.raises_by_url:
            raise RuntimeError("timeout")
        return self.response_by_url[url]


class JobLinkHealthTests(unittest.TestCase):
    def setUp(self):
        _JOB_URL_VALIDATION_CACHE.clear()

    def test_classify_job_url_verdicts(self):
        self.assertEqual(classify_job_url_validation_verdict(404, ""), "bad")
        self.assertEqual(
            classify_job_url_validation_verdict(200, "<html><body>Job Not Found. The role could not be found.</body></html>"),
            "bad",
        )
        self.assertEqual(
            classify_job_url_validation_verdict(403, "<html><body>Access denied</body></html>"),
            "unknown",
        )
        self.assertEqual(classify_job_url_validation_verdict(200, "<html><body>Active role</body></html>"), "good")

    def test_validate_job_link_reuses_cache(self):
        url = "https://www.themuse.com/jobs/acme/software-engineer"
        first_client = _FakeClient(
            response_by_url={
                url: _FakeResponse(
                    status_code=200,
                    text="<html><body>Live job page</body></html>",
                    url=url,
                )
            }
        )
        second_client = _FakeClient(
            response_by_url={
                url: _FakeResponse(
                    status_code=503,
                    text="Job Not Found",
                    url=url,
                )
            }
        )

        first = validate_job_link(url, client=first_client)
        second = validate_job_link(url, client=second_client)

        self.assertEqual(first.status, "good")
        self.assertEqual(second.status, "good")
        self.assertEqual(first_client.calls, [url])
        self.assertEqual(second_client.calls, [])
        self.assertTrue(first.body_preview)

    def test_apply_portal_and_source_tags(self):
        apply_url = "https://jobs.ashbyhq.com/acme/roles/backend-engineer"
        self.assertEqual(classify_apply_portal(apply_url), "ashby")
        self.assertEqual(classify_apply_portal(None), "missing")

        tags = build_source_tags(
            provider="the_muse",
            provider_url="https://www.themuse.com/jobs/acme/software-engineer",
            apply_url=apply_url,
            apply_portal="ashby",
        )
        self.assertIn("provider:the_muse", tags)
        self.assertIn("landing_host:www.themuse.com", tags)
        self.assertIn("apply_host:jobs.ashbyhq.com", tags)
        self.assertIn("apply_portal:ashby", tags)


if __name__ == "__main__":
    unittest.main()
