from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from app.scrapers.base.BaseProviderAdapter import BaseProviderAdapter, ProviderOptedOutError
from app.scrapers.providers import DUMMY_PENDING_MESSAGE, DummyProviderAdapter
from app.scrapers import registry as scraper_registry


class _DummyResponse:
    status_code = 200
    text = "ok"


class _RecordingClient:
    last_init_kwargs = None

    def __init__(self, *args, **kwargs):
        type(self).last_init_kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def request(self, method, url, params=None, json=None):
        return _DummyResponse()


class _DummyAdapter(BaseProviderAdapter):
    def __init__(self, *, rate_limit_seconds: float = 2.0, opted_out: bool = False) -> None:
        super().__init__()
        self._rate_limit_seconds = rate_limit_seconds
        self._opted_out = opted_out

    def get_provider_name(self) -> str:
        return "Dummy Provider"

    def get_base_url(self) -> str:
        return "https://example.com"

    def get_rate_limit_seconds(self) -> float:
        return self._rate_limit_seconds

    def fetch_listings(self, query: str | None, location: str | None, page: int) -> list[dict]:
        del query, location, page
        return [{"provider_job_id": "1"}]

    def normalize_listing(self, raw: dict):
        del raw
        raise NotImplementedError

    def get_opt_out_status(self) -> bool:
        return self._opted_out


class _OptedOutRegistryAdapter(_DummyAdapter):
    def get_provider_name(self) -> str:
        return "Opted Out Provider"

    def get_opt_out_status(self) -> bool:
        return True


class BaseProviderAdapterTests(unittest.TestCase):
    def test_request_enforces_one_second_floor_even_when_adapter_returns_less(self):
        adapter = _DummyAdapter(rate_limit_seconds=0.25)
        adapter._last_request_at = 100.0

        with patch("app.scrapers.base.BaseProviderAdapter.httpx.Client", _RecordingClient), patch(
            "app.scrapers.base.BaseProviderAdapter.time.monotonic",
            side_effect=[100.25, 101.25],
        ), patch("app.scrapers.base.BaseProviderAdapter.time.sleep") as sleep_mock, patch.object(
            adapter,
            "check_robots_txt",
            return_value={"allowed": True, "crawl_delay": None, "disallowed_paths": []},
        ), patch.object(adapter, "_path_allowed", return_value=True):
            adapter._request("GET", "https://example.com/jobs")

        self.assertAlmostEqual(sleep_mock.call_args.args[0], 0.75, places=2)
        self.assertEqual(
            _RecordingClient.last_init_kwargs["headers"]["User-Agent"],
            "UAHBot/1.0; +https://uahapp.com/scraping-policy",
        )

    def test_request_honors_higher_robots_crawl_delay(self):
        adapter = _DummyAdapter(rate_limit_seconds=2.0)
        adapter._last_request_at = 100.0

        with patch("app.scrapers.base.BaseProviderAdapter.httpx.Client", _RecordingClient), patch(
            "app.scrapers.base.BaseProviderAdapter.time.monotonic",
            side_effect=[101.0, 102.0],
        ), patch("app.scrapers.base.BaseProviderAdapter.time.sleep") as sleep_mock, patch.object(
            adapter,
            "check_robots_txt",
            return_value={"allowed": True, "crawl_delay": 5.0, "disallowed_paths": ["/private"]},
        ), patch.object(adapter, "_path_allowed", return_value=True):
            adapter._request("GET", "https://example.com/jobs")

        self.assertAlmostEqual(sleep_mock.call_args.args[0], 4.0, places=2)

    def test_request_raises_when_provider_is_opted_out(self):
        adapter = _DummyAdapter(opted_out=True)

        with self.assertRaises(ProviderOptedOutError):
            adapter._request("GET", "https://example.com/jobs")


class RegistryTests(unittest.TestCase):
    def test_registry_is_seeded_with_dummy_provider_and_excludes_inactive_adapter(self):
        adapter = scraper_registry.get_provider("dummy provider")

        self.assertIsInstance(adapter, DummyProviderAdapter)
        self.assertEqual([item.get_provider_name() for item in scraper_registry.get_all_providers()], ["Dummy Provider"])
        self.assertEqual(scraper_registry.get_active_providers(), [])

    def test_registry_returns_opted_out_adapters(self):
        with patch.dict(scraper_registry._REGISTERED_PROVIDERS, {}, clear=True):
            scraper_registry.register_provider(DummyProviderAdapter())
            scraper_registry.register_provider(_OptedOutRegistryAdapter())

            opted_out = scraper_registry.get_opted_out_providers()

        self.assertEqual([adapter.get_provider_name() for adapter in opted_out], ["Opted Out Provider"])


class DummyProviderAdapterTests(unittest.TestCase):
    def test_stub_is_inactive_and_raises_pending_message(self):
        adapter = DummyProviderAdapter()

        self.assertFalse(adapter.is_active())
        with self.assertRaises(NotImplementedError) as fetch_error:
            adapter.fetch_listings(query=None, location=None, page=1)
        with self.assertRaises(NotImplementedError) as normalize_error:
            adapter.normalize_listing({})

        self.assertEqual(str(fetch_error.exception), DUMMY_PENDING_MESSAGE)
        self.assertEqual(str(normalize_error.exception), DUMMY_PENDING_MESSAGE)


class IgnoreRulesTests(unittest.TestCase):
    def test_gitignore_keeps_gitkeep_and_ignores_generated_logs(self):
        root = Path(__file__).resolve().parents[2]
        gitignore_path = root / ".gitignore"
        gitkeep_path = root / "backend" / "app" / "scrapers" / "checklist" / "checklist_log" / ".gitkeep"
        gitignore_text = gitignore_path.read_text(encoding="utf-8")

        self.assertTrue(gitkeep_path.exists())
        self.assertIn("backend/app/scrapers/checklist/checklist_log/*", gitignore_text)
        self.assertIn("!backend/app/scrapers/checklist/checklist_log/.gitkeep", gitignore_text)


if __name__ == "__main__":
    unittest.main()
