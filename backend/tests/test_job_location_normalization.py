from __future__ import annotations

import unittest

from app.services.job_location_normalization import normalize_job_location_country


class JobLocationNormalizationTests(unittest.TestCase):
    def test_normalizes_representative_locations(self):
        self.assertEqual(normalize_job_location_country("Huntsville, AL"), ("US", "United States"))
        self.assertEqual(
            normalize_job_location_country("Essen, North Rhine-Westphalia, Germany"),
            ("DE", "Germany"),
        )
        self.assertEqual(normalize_job_location_country("Toronto, ON, Canada"), ("CA", "Canada"))

    def test_ambiguous_or_unknown_locations_stay_blank(self):
        self.assertEqual(normalize_job_location_country("Springfield"), (None, None))
        self.assertEqual(normalize_job_location_country(""), (None, None))


if __name__ == "__main__":
    unittest.main()
