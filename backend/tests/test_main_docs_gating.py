from __future__ import annotations

import unittest

from app.core.runtime_environment import generated_docs_enabled


class GeneratedDocsEnvironmentTests(unittest.TestCase):
    def test_generated_docs_enabled_for_explicit_local_and_dev_labels(self):
        for raw_environment in ("development", "dev", "local", " Development "):
            with self.subTest(raw_environment=raw_environment):
                self.assertTrue(generated_docs_enabled(raw_environment))

    def test_generated_docs_disabled_when_environment_is_missing_or_unknown(self):
        for raw_environment in (None, "", "beta", "production", "unknown"):
            with self.subTest(raw_environment=raw_environment):
                self.assertFalse(generated_docs_enabled(raw_environment))


if __name__ == "__main__":
    unittest.main()
