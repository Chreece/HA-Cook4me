from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RecommendFilterUiContractTests(unittest.TestCase):
    def test_recommend_tab_is_filter_and_results_only(self):
        source = (ROOT / "custom_components/cook4me/frontend/cook4me-panel-v15.js").read_text(encoding="utf-8")
        self.assertIn('"cook4me/v13/recommend"', source)
        self.assertIn('id="recommendDiet"', source)
        self.assertIn('id="recommendQuery"', source)
        self.assertNotIn('id="recommendHouseCatalog"', source)
        self.assertNotIn('_recommendHouseEditorHtml()', source)

    def test_backend_applies_query_diet_and_stored_house_inventory(self):
        source = (ROOT / "custom_components/cook4me/websocket_v13.py").read_text(encoding="utf-8")
        self.assertIn("query=query", source)
        self.assertIn('profile["diet"] = diet', source)
        self.assertIn('profile.get("houseIngredients")', source)
        self.assertIn("enrich_match_with_house_keys", source)


if __name__ == "__main__":
    unittest.main()
