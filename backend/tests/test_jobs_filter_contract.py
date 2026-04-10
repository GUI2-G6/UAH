import unittest
from types import SimpleNamespace

from app.api.routes import (
    _build_jobs_filter_metadata_payload,
    _canonicalize_selected_locations,
    _expand_category_for_muse,
    _is_job_allowed_by_preferences,
    _job_matches_keyword,
    _job_matches_posted_after,
    _parse_posted_after_input,
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


class JobsFilterContractTests(unittest.TestCase):
    def test_filter_metadata_has_version_hash_and_cap(self):
        payload = _build_jobs_filter_metadata_payload()
        self.assertEqual(payload.get("metadata_version"), "jobs-filter-v1")
        self.assertTrue(payload.get("metadata_hash"))
        self.assertGreaterEqual(int(payload.get("location_param_cap") or 0), 1)
        self.assertTrue(payload.get("category_groups"))
        self.assertTrue(payload.get("levels"))

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


if __name__ == "__main__":
    unittest.main()
