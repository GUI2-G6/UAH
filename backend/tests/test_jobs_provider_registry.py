from __future__ import annotations

import unittest

from app.providers.registry import (
    get_provider_controls,
    get_provider_definition,
    list_enabled_provider_names,
    list_provider_statuses,
)


class ProviderRegistryTests(unittest.TestCase):
    def test_default_provider_controls_match_rollout_expectations(self):
        muse = get_provider_controls("the_muse")
        arbeitnow = get_provider_controls("arbeitnow")
        jooble = get_provider_controls("jooble")

        self.assertTrue(muse.ingest_enabled)
        self.assertTrue(muse.display_enabled)
        self.assertTrue(muse.scheduled_enabled)
        self.assertTrue(arbeitnow.ingest_enabled)
        self.assertTrue(arbeitnow.display_enabled)
        self.assertTrue(arbeitnow.scheduled_enabled)
        self.assertFalse(jooble.ingest_enabled)
        self.assertFalse(jooble.display_enabled)
        self.assertFalse(jooble.scheduled_enabled)

    def test_registry_exposes_attribution_and_sweep_metadata(self):
        definition = get_provider_definition("adzuna")
        payload = list_provider_statuses()
        provider_names = {row["provider"] for row in payload}

        self.assertEqual(definition.sweep_mode, "category")
        self.assertIn("adzuna", provider_names)
        adzuna_row = next(row for row in payload if row["provider"] == "adzuna")
        self.assertEqual(adzuna_row["attribution"]["label"], "Jobs by Adzuna")
        self.assertTrue("the_muse" in list_enabled_provider_names(control_name="display"))


if __name__ == "__main__":
    unittest.main()
