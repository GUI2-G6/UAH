import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.api.routes import (
    _JOB_URL_VALIDATION_CACHE,
    _build_jobs_filter_metadata_payload,
    _classify_job_url_validation_verdict,
    _canonicalize_selected_locations,
    _expand_category_for_muse,
    _is_job_not_found_signature,
    _is_job_allowed_by_preferences,
    _is_muse_landing_job_url,
    _job_matches_keyword,
    _job_matches_posted_after,
    _parse_posted_after_input,
    _strip_location_params,
    _should_run_location_relaxed_fallback,
    _validate_candidate_job_urls,
)


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self._rows


class _FakeDb:
    def __init__(self, rows):
        self._rows = rows

    def query(self, _model):
        return _FakeQuery(self._rows)


class _FakeHttpResponse:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text


class _FakeHttpClient:
    def __init__(self, response_by_url=None, raises_by_url=None):
        self.response_by_url = response_by_url or {}
        self.raises_by_url = raises_by_url or set()
        self.calls = []

    async def get(self, url):
        self.calls.append(url)
        if url in self.raises_by_url:
            raise RuntimeError("network timeout")
        return self.response_by_url.get(url, _FakeHttpResponse(status_code=200, text="ok"))


class JobsFilterContractTests(unittest.TestCase):
    def setUp(self):
        _JOB_URL_VALIDATION_CACHE.clear()

    def test_filter_metadata_has_version_hash_and_cap(self):
        payload = _build_jobs_filter_metadata_payload()
        self.assertEqual(payload.get("metadata_version"), "jobs-filter-v2")
        self.assertTrue(payload.get("metadata_hash"))
        self.assertGreaterEqual(int(payload.get("location_param_cap") or 0), 1)
        self.assertTrue(payload.get("category_groups"))
        self.assertTrue(payload.get("levels"))
        self.assertTrue(payload.get("category_values"))
        self.assertTrue(payload.get("level_values"))

    @patch("app.api.routes._query_observed_level_counts")
    @patch("app.api.routes._query_observed_category_counts")
    def test_filter_metadata_uses_sorted_observed_values(self, category_mock, level_mock):
        category_mock.return_value = [
            ("Software Engineer", 4),
            ("Design", 2),
            ("Data Science", 4),
        ]
        level_mock.return_value = [
            ("senior", 3),
            ("entry", 5),
            ("vp", 1),
        ]

        payload = _build_jobs_filter_metadata_payload(db=object())

        self.assertEqual(
            payload.get("category_values"),
            [
                {"value": "Data Science", "observed_count": 4},
                {"value": "Software Engineer", "observed_count": 4},
                {"value": "Design", "observed_count": 2},
            ],
        )
        self.assertEqual(
            payload.get("level_values"),
            [
                {"value": "entry", "label": "Entry", "observed_count": 5},
                {"value": "senior", "label": "Senior", "observed_count": 3},
                {"value": "vp", "label": "VP", "observed_count": 1},
            ],
        )
        self.assertEqual(payload.get("levels"), ["Entry", "Senior", "VP"])

    @patch("app.api.routes._query_observed_level_counts", return_value=[])
    @patch("app.api.routes._query_observed_category_counts", return_value=[])
    def test_filter_metadata_falls_back_when_catalog_is_empty(self, _category_mock, _level_mock):
        payload = _build_jobs_filter_metadata_payload(db=object())

        self.assertTrue(payload.get("category_values"))
        self.assertTrue(payload.get("level_values"))
        self.assertTrue(all(int(item.get("observed_count") or 0) == 0 for item in payload["category_values"]))
        self.assertTrue(all(int(item.get("observed_count") or 0) == 0 for item in payload["level_values"]))
        self.assertTrue(any(item.get("value") == "Software Engineer" for item in payload["category_values"]))
        self.assertTrue(any(item.get("value") == "entry" for item in payload["level_values"]))

    def test_category_expansion_allows_group_and_passthrough(self):
        expanded_group = _expand_category_for_muse("tech")
        self.assertIn("Software Engineer", expanded_group)

        passthrough = _expand_category_for_muse("Quantum Networking")
        self.assertEqual(passthrough, ["Quantum Networking"])

    def test_keyword_and_posted_after_helpers(self):
        mapped_job = {
            "name": "Backend Engineer",
            "short_name": "Backend Engineer",
            "company": "Data Forge",
            "contents": "Build APIs and background processing pipelines.",
            "locations": ["Austin, TX"],
            "categories": ["Software Engineer"],
            "levels": ["Senior Level"],
            "tags": ["Python"],
            "publication_date": "2026-04-02T11:30:00Z",
        }

        self.assertTrue(_job_matches_keyword(mapped_job, "background processing"))
        self.assertFalse(_job_matches_keyword(mapped_job, "frontend vue"))

        threshold = _parse_posted_after_input("2026-04-01")
        self.assertIsNotNone(threshold)
        self.assertTrue(_job_matches_posted_after(mapped_job, threshold))

        late_threshold = _parse_posted_after_input("2026-04-05")
        self.assertFalse(_job_matches_posted_after(mapped_job, late_threshold))

    def test_country_mode_canonicalization_reports_truncation(self):
        rows = [
            SimpleNamespace(location_name="Boston, MA", observed_count=900),
            SimpleNamespace(location_name="Seattle, WA", observed_count=800),
            SimpleNamespace(location_name="Austin, TX", observed_count=700),
        ]
        fake_db = _FakeDb(rows)

        selected, diagnostics = _canonicalize_selected_locations(
            raw_locations=["Boston", "Seattle", "Austin"],
            location_mode="country",
            location_country_code="US",
            location_param_cap=2,
            db=fake_db,
        )

        self.assertEqual(selected, ["Boston, MA", "Seattle, WA"])
        self.assertEqual(diagnostics.get("requested_unique_count"), 3)
        self.assertEqual(diagnostics.get("dropped_count"), 1)
        self.assertEqual(diagnostics.get("strategy"), "muse-index-country-aware")

    def test_remote_off_policy_allows_constraint_overlap(self):
        allowed, reason = _is_job_allowed_by_preferences(
            has_remote=True,
            has_hybrid=False,
            include_remote=False,
            include_hybrid=True,
            job_locations=["Remote"],
            selected_locations=["Boston, MA"],
            allow_local_compatible_remote=True,
        )
        self.assertTrue(allowed)
        self.assertEqual(reason, "constraint_overlap")

    def test_remote_off_policy_blocks_non_compatible_remote(self):
        allowed, reason = _is_job_allowed_by_preferences(
            has_remote=True,
            has_hybrid=False,
            include_remote=False,
            include_hybrid=True,
            job_locations=["Remote"],
            selected_locations=["Boston, MA"],
            allow_local_compatible_remote=False,
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, "no-match")

    def test_muse_landing_url_validation_helpers(self):
        self.assertTrue(_is_muse_landing_job_url("https://www.themuse.com/jobs/acme/software-engineer"))
        self.assertTrue(_is_muse_landing_job_url("https://themuse.com/jobs/acme/software-engineer?ref=feed"))
        self.assertFalse(_is_muse_landing_job_url("https://www.themuse.com/companies/acme"))
        self.assertFalse(_is_muse_landing_job_url("https://example.com/jobs/acme/software-engineer"))

    def test_job_url_verdict_classification(self):
        self.assertEqual(_classify_job_url_validation_verdict(503, ""), "bad")
        not_found_html = "<h1>Job Not Found</h1><p>The job posting you're looking for could not be found.</p>"
        self.assertTrue(_is_job_not_found_signature(not_found_html))
        self.assertEqual(_classify_job_url_validation_verdict(200, not_found_html), "bad")
        self.assertEqual(_classify_job_url_validation_verdict(200, "<html><body>Legit posting</body></html>"), "good")
        self.assertEqual(_classify_job_url_validation_verdict(429, ""), "unknown")

    def test_location_relaxed_fallback_trigger_guard(self):
        self.assertTrue(
            _should_run_location_relaxed_fallback(
                page=1,
                accepted_jobs_count=0,
                selected_locations=["Boston, MA"],
                location_relaxed_fallback=False,
            )
        )
        self.assertFalse(
            _should_run_location_relaxed_fallback(
                page=2,
                accepted_jobs_count=0,
                selected_locations=["Boston, MA"],
                location_relaxed_fallback=False,
            )
        )
        self.assertFalse(
            _should_run_location_relaxed_fallback(
                page=1,
                accepted_jobs_count=4,
                selected_locations=["Boston, MA"],
                location_relaxed_fallback=False,
            )
        )
        self.assertFalse(
            _should_run_location_relaxed_fallback(
                page=1,
                accepted_jobs_count=0,
                selected_locations=[],
                location_relaxed_fallback=False,
            )
        )

    def test_location_relaxed_fallback_param_strip_only_removes_location(self):
        params = [
            ("api_key", "demo"),
            ("location", "Boston, MA"),
            ("category", "Software Engineering"),
            ("level", "Entry Level"),
            ("location", "New York, NY"),
            ("company", "Acme"),
        ]
        stripped = _strip_location_params(params)
        self.assertEqual(
            stripped,
            [
                ("api_key", "demo"),
                ("category", "Software Engineering"),
                ("level", "Entry Level"),
                ("company", "Acme"),
            ],
        )

    def test_url_validation_marks_bad_and_reuses_cache(self):
        bad_url = "https://www.themuse.com/jobs/acme/stale-role"
        good_url = "https://www.themuse.com/jobs/acme/valid-role"
        candidates = [
            ({"job_url": bad_url, "id": 1}, "concrete_location"),
            ({"job_url": good_url, "id": 2}, "concrete_location"),
        ]
        first_client = _FakeHttpClient(
            response_by_url={
                bad_url: _FakeHttpResponse(status_code=503, text="Job Not Found"),
                good_url: _FakeHttpResponse(status_code=200, text="<html>Active job</html>"),
            }
        )

        filtered_first, stats_first = asyncio.run(
            _validate_candidate_job_urls(candidates, url_client=first_client, remaining_checks=10)
        )
        self.assertEqual(len(filtered_first), 1)
        self.assertEqual(filtered_first[0][0]["job_url"], good_url)
        self.assertEqual(stats_first.get("dropped_count"), 1)
        self.assertEqual(stats_first.get("checked_count"), 2)
        self.assertEqual(stats_first.get("cache_hit_count"), 0)
        self.assertEqual(stats_first.get("request_count"), 2)

        cached_client = _FakeHttpClient()
        filtered_cached, stats_cached = asyncio.run(
            _validate_candidate_job_urls(candidates, url_client=cached_client, remaining_checks=10)
        )
        self.assertEqual(len(filtered_cached), 1)
        self.assertEqual(filtered_cached[0][0]["job_url"], good_url)
        self.assertEqual(stats_cached.get("dropped_count"), 1)
        self.assertEqual(stats_cached.get("checked_count"), 2)
        self.assertEqual(stats_cached.get("cache_hit_count"), 2)
        self.assertEqual(stats_cached.get("request_count"), 0)
        self.assertEqual(cached_client.calls, [])

    def test_url_validation_timeout_stays_eligible(self):
        timed_out_url = "https://www.themuse.com/jobs/acme/flaky-role"
        candidates = [({"job_url": timed_out_url, "id": 3}, "concrete_location")]
        flaky_client = _FakeHttpClient(raises_by_url={timed_out_url})

        filtered, stats = asyncio.run(
            _validate_candidate_job_urls(candidates, url_client=flaky_client, remaining_checks=5)
        )
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0][0]["job_url"], timed_out_url)
        self.assertEqual(stats.get("dropped_count"), 0)
        self.assertEqual(stats.get("checked_count"), 1)
        self.assertEqual(stats.get("request_count"), 1)


if __name__ == "__main__":
    unittest.main()
