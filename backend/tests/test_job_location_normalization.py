from __future__ import annotations

import unittest

from app.services.job_location_normalization import normalize_job_location_country


class JobLocationNormalizationTests(unittest.TestCase):
    def test_normalizes_state_and_explicit_country_context(self):
        cases = {
            "Huntsville, AL": ("US", "United States"),
            "San Francisco, CA": ("US", "United States"),
            "Los Angeles, CA": ("US", "United States"),
            "Indianapolis, IN": ("US", "United States"),
            "Wilmington, DE": ("US", "United States"),
            "Bangor, ME": ("US", "United States"),
            "Portland, OR": ("US", "United States"),
            "Atlanta, GA": ("US", "United States"),
            "San Francisco, CA, USA": ("US", "United States"),
            "Essen, North Rhine-Westphalia, Germany": ("DE", "Germany"),
            "Toronto, ON, Canada": ("CA", "Canada"),
        }

        for raw_location, expected in cases.items():
            with self.subTest(location=raw_location):
                self.assertEqual(normalize_job_location_country(raw_location), expected)

    def test_normalizes_washington_and_us_subregion_formats(self):
        cases = {
            "Washington DC": ("US", "United States"),
            "Washington, DC": ("US", "United States"),
            "New York, New York County": ("US", "United States"),
            "Chicago, Cook County": ("US", "United States"),
            "Brooklyn, Williamsburg": ("US", "United States"),
        }

        for raw_location, expected in cases.items():
            with self.subTest(location=raw_location):
                self.assertEqual(normalize_job_location_country(raw_location), expected)

    def test_city_only_locations_use_dominant_country_lookup(self):
        cases = {
            "Berlin": ("DE", "Germany"),
            "Hamburg": ("DE", "Germany"),
            "Warsaw": ("PL", "Poland"),
            "Paris": ("FR", "France"),
        }

        for raw_location, expected in cases.items():
            with self.subTest(location=raw_location):
                self.assertEqual(normalize_job_location_country(raw_location), expected)

    def test_remote_or_unknown_locations_stay_blank(self):
        for raw_location in ("Remote", "Flexible / Remote", "Worldwide", "Springfield", ""):
            with self.subTest(location=raw_location):
                self.assertEqual(normalize_job_location_country(raw_location), (None, None))


if __name__ == "__main__":
    unittest.main()
