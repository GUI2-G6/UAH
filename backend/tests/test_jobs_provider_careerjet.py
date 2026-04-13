from __future__ import annotations

import unittest

from app.providers.careerjet import CareerjetJobProvider


class CareerjetProviderTests(unittest.TestCase):
    def test_fetch_raises_explanatory_not_implemented(self):
        provider = CareerjetJobProvider()

        with self.assertRaises(NotImplementedError) as ctx:
            provider.fetch({})

        self.assertIn("background local-cache ingest architecture", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
