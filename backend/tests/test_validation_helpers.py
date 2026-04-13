import unittest

from app.core.validation import (
    build_mailto_href,
    build_phone_href,
    infer_phone_country,
    normalize_phone,
    require_valid_email,
)


class ValidationHelperTests(unittest.TestCase):
    def test_require_valid_email_accepts_plus_and_subdomain(self):
        self.assertEqual(
            require_valid_email("  Jane.Doe+alerts@sub.example.co.uk  "),
            "jane.doe+alerts@sub.example.co.uk",
        )

    def test_require_valid_email_rejects_bad_domain(self):
        with self.assertRaises(ValueError):
            require_valid_email("person@example")

    def test_normalize_phone_formats_us_ten_digit_number(self):
        self.assertEqual(normalize_phone("2565550199"), "(256) 555-0199")

    def test_normalize_phone_formats_us_eleven_digit_number(self):
        self.assertEqual(normalize_phone("1 (256) 555-0199"), "(256) 555-0199")

    def test_normalize_phone_accepts_international_plus_number(self):
        self.assertEqual(normalize_phone("+44 20 7946 0958"), "+442079460958")

    def test_normalize_phone_rejects_letters(self):
        with self.assertRaises(ValueError):
            normalize_phone("555-CALLNOW")

    def test_normalize_phone_rejects_too_few_digits(self):
        with self.assertRaises(ValueError):
            normalize_phone("12345")

    def test_normalize_phone_rejects_too_many_digits(self):
        with self.assertRaises(ValueError):
            normalize_phone("+1234567890123456")

    def test_build_mailto_href_returns_empty_for_invalid_value(self):
        self.assertEqual(build_mailto_href("not-an-email"), "")

    def test_build_phone_href_formats_us_and_international_numbers(self):
        self.assertEqual(build_phone_href("(256) 555-0199"), "tel:+12565550199")
        self.assertEqual(build_phone_href("+91 98765 43210"), "tel:+919876543210")

    def test_infer_phone_country_uses_us_domestic_default(self):
        self.assertEqual(
            infer_phone_country("(256) 555-0199"),
            {"code": "US", "label": "United States"},
        )

    def test_infer_phone_country_recognizes_explicit_country_code(self):
        self.assertEqual(
            infer_phone_country("+44 20 7946 0958"),
            {"code": "GB", "label": "United Kingdom"},
        )

    def test_infer_phone_country_hides_unknown_international_code(self):
        self.assertIsNone(infer_phone_country("+999123456789"))


if __name__ == "__main__":
    unittest.main()
