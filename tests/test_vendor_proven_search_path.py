from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    package = types.ModuleType("cook4me_vendor_proven_test")
    package.__path__ = []
    catalog = types.ModuleType("cook4me_vendor_proven_test.cook4me_recipe_catalog")
    catalog.c4m = types.SimpleNamespace(curl_requests=object())
    enriched = types.ModuleType("cook4me_vendor_proven_test.cook4me_recipe_detail_enriched")
    enriched.recipe_detail = lambda *args, **kwargs: {}
    sys.modules["cook4me_vendor_proven_test"] = package
    sys.modules["cook4me_vendor_proven_test.cook4me_recipe_catalog"] = catalog
    sys.modules["cook4me_vendor_proven_test.cook4me_recipe_detail_enriched"] = enriched
    spec = importlib.util.spec_from_file_location(
        "cook4me_vendor_proven_test.cook4me_recipe_search_proven",
        ROOT / "custom_components/cook4me/vendor/cook4me_recipe_search_proven.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class VendorProvenSearchPathTests(unittest.TestCase):
    def test_exact_body_matches_standalone_proof(self):
        module = load_module()
        self.assertEqual(module.SEARCH_CONTRACT, "standalone-proven-cookeo-brand-v5")
        self.assertEqual(
            module.search_body("de", "GS_DE"),
            {
                "fieldFilters": [
                    {"field": "lang.key", "values": ["de"]},
                    {"field": "market.key", "values": ["GS_DE"]},
                    {
                        "field": "applianceGroups.reference.key",
                        "values": ["APPLIANCE_GROUP_15"],
                    },
                    {"field": "topRecipe.type.key", "values": ["BRAND"]},
                ]
            },
        )

    def test_vendor_cli_routes_search_to_proven_module(self):
        source = (
            ROOT / "custom_components/cook4me/vendor/cook4me_auto.py"
        ).read_text(encoding="utf-8")
        self.assertIn("import cook4me_recipe_search_proven as proven_search", source)
        self.assertIn("proven_search.search_recipes", source)
        search_branch = source.split("if a.command=='search-recipes':", 1)[1].split("; return", 1)[0]
        self.assertNotIn("c4m.search_recipes", search_branch)

    def test_vendor_cli_routes_recipe_metadata_to_enriched_detail(self):
        source = (
            ROOT / "custom_components/cook4me/vendor/cook4me_auto.py"
        ).read_text(encoding="utf-8")
        self.assertIn("import cook4me_recipe_detail_enriched as enriched_detail", source)
        metadata_branch = source.split("if a.command=='recipe-metadata':", 1)[1].split("; return", 1)[0]
        self.assertIn("enriched_detail.recipe_detail", metadata_branch)
        self.assertNotIn("c4m.recipe_metadata", metadata_branch)


if __name__ == "__main__":
    unittest.main()
