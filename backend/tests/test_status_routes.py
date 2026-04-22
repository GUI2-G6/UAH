from __future__ import annotations

import asyncio
import inspect
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi.params import Depends as DependsParam

from app.api import routes as routes_api


def _collect_keys(payload):
    keys = set()
    if isinstance(payload, dict):
        for key, value in payload.items():
            keys.add(key)
            keys.update(_collect_keys(value))
    elif isinstance(payload, list):
        for item in payload:
            keys.update(_collect_keys(item))
    return keys


class PublicStatusRouteTests(unittest.TestCase):
    def test_api_status_returns_dynamic_public_safe_shape(self):
        db = Mock()
        db.execute.side_effect = [
            Mock(fetchone=Mock(return_value=None)),
            Mock(fetchone=Mock(return_value=("PostgreSQL 16.4",))),
        ]
        pipeline_payload = {
            "cloud": {"available": True, "degraded": False, "reachable": True},
            "local": {"available": True, "degraded": False, "reachable": True},
            "rules": {"available": True, "degraded": False, "reachable": True},
        }

        with patch.object(routes_api, "get_pipeline_availability", AsyncMock(return_value=pipeline_payload)):
            payload = asyncio.run(routes_api.api_status(db=db))

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["overall"], "healthy")
        self.assertIn("environment", payload)
        self.assertEqual(payload["message"], "UAH API is running")
        self.assertIn("timestamp", payload)
        self.assertIn("services", payload)
        self.assertIn("service_summaries", payload)
        self.assertEqual(payload["services"]["database"]["status"], "healthy")
        self.assertEqual(payload["services"]["database"]["postgres_version"], "PostgreSQL 16.4")
        self.assertEqual(payload["services"]["resume_parsing"]["available_methods"], 3)

        payload_keys = _collect_keys(payload)
        for sensitive_key in (
            "pid",
            "host",
            "hostname",
            "database_name",
            "db_name",
            "db_user",
            "user",
            "stack",
            "stacktrace",
            "traceback",
        ):
            with self.subTest(sensitive_key=sensitive_key):
                self.assertNotIn(sensitive_key, payload_keys)

    def test_api_status_sanitizes_failures_and_avoids_internal_errors(self):
        db = Mock()
        db.execute.side_effect = RuntimeError(
            "connection failed for host=internal-db user=postgres db=uah"
        )

        with patch.object(
            routes_api,
            "get_pipeline_availability",
            AsyncMock(side_effect=RuntimeError("Traceback: parse service timeout")),
        ):
            payload = asyncio.run(routes_api.api_status(db=db))

        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["overall"], "unhealthy")
        self.assertEqual(
            payload["message"],
            "UAH API is experiencing service disruption",
        )
        self.assertEqual(payload["services"]["database"]["status"], "unhealthy")
        self.assertEqual(
            payload["services"]["database"]["summary"],
            "Database connectivity check failed.",
        )
        self.assertEqual(payload["services"]["database"]["postgres_version"], "unavailable")
        self.assertEqual(payload["services"]["resume_parsing"]["status"], "degraded")

        encoded = json.dumps(payload).lower()
        self.assertNotIn("traceback", encoded)
        self.assertNotIn("internal-db", encoded)
        self.assertNotIn("user=postgres", encoded)
        self.assertNotIn("db=uah", encoded)

    def test_diagnostics_route_stays_admin_guarded(self):
        signature = inspect.signature(routes_api.diagnostics)
        current_user_parameter = signature.parameters["current_user"]
        dependency = current_user_parameter.default

        self.assertIsInstance(dependency, DependsParam)
        self.assertIs(dependency.dependency, routes_api.require_admin_user)


if __name__ == "__main__":
    unittest.main()
