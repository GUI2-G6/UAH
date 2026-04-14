from __future__ import annotations

import unittest

from app.providers.adzuna import AdzunaJobProvider


class AdzunaProviderTests(unittest.TestCase):
    def test_classify_landing_page_verdict_marks_expired_jobs_bad(self):
        provider = AdzunaJobProvider()

        verdict = provider.classify_landing_page_verdict(
            url="https://www.adzuna.co.uk/jobs/details/123",
            status_code=200,
            body_text="<html><body><h1>This job has expired</h1></body></html>",
        )

        self.assertEqual(verdict, "bad")

    def test_classify_landing_page_verdict_keeps_active_jobs_good(self):
        provider = AdzunaJobProvider()

        verdict = provider.classify_landing_page_verdict(
            url="https://www.adzuna.co.uk/jobs/details/456",
            status_code=200,
            body_text="<html><body><h1>Backend Engineer</h1><p>Apply now</p></body></html>",
        )

        self.assertEqual(verdict, "good")


if __name__ == "__main__":
    unittest.main()
