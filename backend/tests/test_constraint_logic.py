import unittest

from app.api.routes import (
    _confidence_meets_threshold,
    _extract_location_constraints,
    _term_matches_selected_locations,
)


class ConstraintLogicTests(unittest.TestCase):
    def test_confidence_threshold(self):
        self.assertTrue(_confidence_meets_threshold("high", "high"))
        self.assertTrue(_confidence_meets_threshold("high", "medium"))
        self.assertFalse(_confidence_meets_threshold("medium", "high"))

    def test_extract_constraints_from_sample_remote_text(self):
        sample_job = {
            "name": "Sales Engineer",
            "short_name": "Sales Engineer",
            "contents": (
                "This is a remote position open to candidates residing in the US within the "
                "Central or Mountain time zone except the San Francisco Bay Metro Area, "
                "NYC Metro Area, and Washington, D.C. Metro Area."
            ),
        }

        constraints = _extract_location_constraints(sample_job, ["Flexible / Remote"])

        self.assertIn("CT", constraints.get("include_timezone_families", []))
        self.assertIn("MT", constraints.get("include_timezone_families", []))
        self.assertIn("united states", constraints.get("include_location_terms", []))
        self.assertTrue(any("bay" in item for item in constraints.get("exclude_location_terms", [])))
        self.assertEqual(constraints.get("confidence"), "high")

    def test_metro_alias_overlap(self):
        selected_locations = ["Lowell, MA", "Boston, MA", "Cambridge, MA"]
        self.assertFalse(_term_matches_selected_locations("San Francisco Bay Metro Area", selected_locations, "US"))
        self.assertFalse(_term_matches_selected_locations("NYC Metro Area", selected_locations, "US"))

        nyc_selected = ["New York, NY", "Jersey City, NJ"]
        self.assertTrue(_term_matches_selected_locations("NYC Metro Area", nyc_selected, "US"))


if __name__ == "__main__":
    unittest.main()
