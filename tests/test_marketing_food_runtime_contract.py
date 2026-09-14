from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "custom_components/cook4me/websocket_v11.py").read_text(encoding="utf-8")


class MarketingFoodRuntimeContractTests(unittest.TestCase):
    def test_runtime_uses_apk_exact_unfiltered_marketing_food_request(self):
        self.assertIn('_MARKETING_FOOD_SIZE = 100000', SOURCE)
        self.assertIn('{"field": "market.key", "values": [market]}', SOURCE)
        self.assertIn('{"field": "name.lang", "values": [language]}', SOURCE)
        self.assertIn('"fieldList": ["key", "name", "mixMedias"]', SOURCE)
        self.assertIn('"facetList": []', SOURCE)
        self.assertIn('"sort": {"name": "name", "direction": "ASC"}', SOURCE)
        self.assertIn('body=_marketing_food_search_body(language, market)', SOURCE)
        self.assertNotIn('body={}', SOURCE)
        self.assertNotIn('"isMixMain"', SOURCE)


if __name__ == "__main__":
    unittest.main()
