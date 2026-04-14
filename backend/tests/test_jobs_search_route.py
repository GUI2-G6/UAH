from __future__ import annotations

import unittest
from unittest.mock import patch

from app.api import jobs as jobs_api


class JobsSearchRouteTests(unittest.TestCase):
    def test_thin_results_queue_sync_and_set_note(self):
        payload = {
            "jobs": [{"id": 1, "name": "Software Engineer"}],
            "total": 1,
            "page": 1,
            "page_size": 20,
            "has_more": False,
            "source": "local_db",
        }

        with patch.object(jobs_api, "search_local_jobs", return_value=dict(payload)), patch.object(
            jobs_api, "_enqueue_thin_results_sync"
        ) as enqueue_mock:
            response = jobs_api.search_jobs(
                category=["tech"],
                catogory=None,
                location=None,
                experience_level=None,
                level=None,
                company=None,
                db=object(),
            )

        enqueue_mock.assert_called_once_with("tech")
        self.assertEqual(response["note"], "results_thin_sync_triggered")

    def test_large_result_set_does_not_queue_sync(self):
        payload = {
            "jobs": [{"id": idx, "name": f"Job {idx}"} for idx in range(12)],
            "total": 12,
            "page": 1,
            "page_size": 20,
            "has_more": False,
            "source": "local_db",
        }

        with patch.object(jobs_api, "search_local_jobs", return_value=dict(payload)), patch.object(
            jobs_api, "_enqueue_thin_results_sync"
        ) as enqueue_mock:
            response = jobs_api.search_jobs(
                category=["tech"],
                catogory=None,
                location=None,
                experience_level=None,
                level=None,
                company=None,
                db=object(),
            )

        enqueue_mock.assert_not_called()
        self.assertIsNone(response["note"])

    def test_sort_by_forwarded_to_local_search(self):
        payload = {
            "jobs": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "has_more": False,
            "source": "local_db",
        }

        with patch.object(jobs_api, "search_local_jobs", return_value=dict(payload)) as search_mock, patch.object(
            jobs_api, "_enqueue_thin_results_sync"
        ):
            jobs_api.search_jobs(
                category=None,
                catogory=None,
                location=None,
                experience_level=None,
                level=None,
                company=None,
                sort_by="quality_desc",
                db=object(),
            )

        self.assertEqual(search_mock.call_args.kwargs["sort_by"], "quality_desc")


if __name__ == "__main__":
    unittest.main()
