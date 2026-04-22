from __future__ import annotations

import base64
import unittest

from app.core.runtime_environment import (
    generated_docs_auth_required,
    generated_docs_authenticate_header,
    generated_docs_enabled,
    internal_surface_auth_required,
    is_generated_docs_path,
    is_internal_surface_path,
)


class GeneratedDocsEnvironmentTests(unittest.TestCase):
    def test_generated_docs_enabled_for_explicit_local_and_dev_labels(self):
        for raw_environment in ("development", "dev", "local", " Development "):
            with self.subTest(raw_environment=raw_environment):
                self.assertTrue(generated_docs_enabled(raw_environment))

    def test_generated_docs_disabled_when_environment_is_missing_or_unknown(self):
        for raw_environment in (None, "", "beta", "production", "unknown"):
            with self.subTest(raw_environment=raw_environment):
                self.assertFalse(generated_docs_enabled(raw_environment))

    def test_generated_docs_enabled_for_beta_when_passcode_is_configured(self):
        self.assertTrue(generated_docs_enabled("beta", "dev-only-passcode"))

    def test_generated_docs_path_matches_docs_endpoints_and_oauth_redirect(self):
        for path in ("/docs", "/docs/oauth2-redirect", "/redoc", "/openapi.json"):
            with self.subTest(path=path):
                self.assertTrue(is_generated_docs_path(path))

    def test_generated_docs_path_ignores_non_docs_routes(self):
        for path in ("/", "/api/health", "/docsness", "/openapi.jsonl"):
            with self.subTest(path=path):
                self.assertFalse(is_generated_docs_path(path))

    def test_beta_docs_auth_rejects_missing_credentials(self):
        requires_auth = generated_docs_auth_required(
            path="/docs",
            raw_environment="beta",
            authorization_header=None,
            expected_username="dev",
            expected_passcode="top-secret",
        )

        self.assertTrue(requires_auth)
        self.assertEqual(generated_docs_authenticate_header(), 'Basic realm="UAH Beta API Docs"')

    def test_beta_docs_auth_allows_valid_basic_auth_credentials(self):
        credentials = base64.b64encode(b"dev:top-secret").decode("ascii")
        requires_auth = generated_docs_auth_required(
            path="/openapi.json",
            raw_environment="beta",
            authorization_header=f"Basic {credentials}",
            expected_username="dev",
            expected_passcode="top-secret",
        )

        self.assertFalse(requires_auth)

    def test_beta_docs_auth_is_not_applied_outside_beta(self):
        requires_auth = generated_docs_auth_required(
            path="/docs",
            raw_environment="production",
            authorization_header=None,
            expected_username="dev",
            expected_passcode="top-secret",
        )

        self.assertFalse(requires_auth)

    def test_internal_surface_path_detection_handles_expected_routes(self):
        for path in (
            "/api/admin",
            "/api/admin/invites",
            "/api/jobs/debug/overview",
            "/api/jobs/debug/probe/provider",
            "/api/diagnostics",
            "/api/geolocation/muse-supported-locations/refresh",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_internal_surface_path(path))

    def test_internal_surface_path_detection_ignores_public_routes(self):
        for path in (
            "/api/",
            "/api/status",
            "/api/jobs/search",
            "/api/jobs/search-live-source",
            "/api/health",
            "/docs",
        ):
            with self.subTest(path=path):
                self.assertFalse(is_internal_surface_path(path))

    def test_internal_surface_auth_not_required_when_key_not_configured(self):
        requires_auth = internal_surface_auth_required(
            path="/api/admin/invites",
            raw_environment="beta",
            provided_key=None,
            expected_key="",
        )

        self.assertFalse(requires_auth)

    def test_internal_surface_auth_required_when_beta_key_missing(self):
        requires_auth = internal_surface_auth_required(
            path="/api/admin/invites",
            raw_environment="beta",
            provided_key=None,
            expected_key="super-secret",
        )

        self.assertTrue(requires_auth)

    def test_internal_surface_auth_allows_matching_key(self):
        requires_auth = internal_surface_auth_required(
            path="/api/jobs/debug/overview",
            raw_environment="production",
            provided_key="super-secret",
            expected_key="super-secret",
        )

        self.assertFalse(requires_auth)


if __name__ == "__main__":
    unittest.main()
