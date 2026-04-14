from __future__ import annotations

import unittest

from app.services.job_location_normalization import normalize_job_location_country


class JobLocationNormalizationTests(unittest.TestCase):
    def test_normalizes_requested_high_priority_cases(self):
        cases = {
            "San Francisco, CA": ("US", "United States"),
            "Oakland, CA": ("US", "United States"),
            "Toronto, ON": ("CA", "Canada"),
            "Vancouver, BC": ("CA", "Canada"),
            "Berlin": ("DE", "Germany"),
            "Hamburg": ("DE", "Germany"),
            "Warsaw, Poland": ("PL", "Poland"),
            "London, UK": ("GB", "United Kingdom"),
            "Sydney, NSW": ("AU", "Australia"),
            "Washington DC": ("US", "United States"),
            "San Diego, San Diego County": ("US", "United States"),
            "Grand Central, Manhattan": ("US", "United States"),
            "West Indianapolis, Marion County": ("US", "United States"),
            "Bonifacio Global City, Philippines": ("PH", "Philippines"),
            "Paris": ("FR", "France"),
            "Amsterdam": ("NL", "Netherlands"),
            "Seoul": ("KR", "South Korea"),
            "Chicago, United States": ("US", "United States"),
            "Irving, Dallas": ("US", "United States"),
        }

        for raw_location, expected in cases.items():
            with self.subTest(location=raw_location):
                self.assertEqual(normalize_job_location_country(raw_location), expected)

    def test_remote_and_location_agnostic_inputs_use_remote_global_sentinel(self):
        cases = {
            "Flexible / Remote": ("XX", "Remote / Global"),
            "Remote": ("XX", "Remote / Global"),
            "Worldwide": ("XX", "Remote / Global"),
            "Global": ("XX", "Remote / Global"),
            "": ("XX", "Remote / Global"),
            None: ("XX", "Remote / Global"),
        }

        for raw_location, expected in cases.items():
            with self.subTest(location=raw_location):
                self.assertEqual(normalize_job_location_country(raw_location), expected)

    def test_non_remote_ambiguous_locations_use_uncertain_sentinel(self):
        cases = {
            "Springfield": ("XU", "Uncertain"),
            "Unknown campus": ("XU", "Uncertain"),
        }

        for raw_location, expected in cases.items():
            with self.subTest(location=raw_location):
                self.assertEqual(normalize_job_location_country(raw_location), expected)


if __name__ == "__main__":
    unittest.main()
