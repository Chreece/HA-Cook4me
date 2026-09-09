from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components" / "cook4me"


def load_package_module(name: str, filename: str):
    package_name = "cook4me_today_multilang_testpkg"
    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(PACKAGE)]
        sys.modules[package_name] = package
    full_name = f"{package_name}.{name}"
    spec = importlib.util.spec_from_file_location(full_name, PACKAGE / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


class TodayMultiLanguageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_package_module("today_logic", "today_logic.py")
        cls.module = load_package_module("today_multilang", "today_multilang.py")

    @staticmethod
    def row(language: str, identity: str, score: float, ingredient: str):
        return {
            "title": f"{language}-{identity}",
            "groupingFunctionalId": identity,
            "todayCatalogLanguage": language,
            "match": {"score": score},
            "ingredients": [{"foodKey": ingredient}],
        }

    def test_two_catalogs_are_both_represented_when_two_results_requested(self):
        rows = [
            self.row("de", "same", 100, "RICE"),
            self.row("de", "de-only", 96, "POTATO"),
            self.row("en", "same", 99, "RICE"),
            self.row("en", "en-only", 95, "LENTIL"),
        ]
        chosen = self.module.select_catalog_balanced(rows, 2, ["de", "en"])
        self.assertEqual(len(chosen), 2)
        self.assertEqual(
            {row["todayCatalogLanguage"] for row in chosen},
            {"de", "en"},
        )
        identities = {row["groupingFunctionalId"] for row in chosen}
        self.assertEqual(len(identities), 2)

    def test_four_results_are_evenly_spread_when_catalogs_have_candidates(self):
        rows = [
            self.row("de", "de1", 100, "A"),
            self.row("de", "de2", 90, "B"),
            self.row("de", "de3", 80, "C"),
            self.row("en", "en1", 99, "D"),
            self.row("en", "en2", 89, "E"),
            self.row("en", "en3", 79, "F"),
        ]
        chosen = self.module.select_catalog_balanced(rows, 4, ["de", "en"])
        counts = {
            language: sum(row["todayCatalogLanguage"] == language for row in chosen)
            for language in ("de", "en")
        }
        self.assertEqual(counts, {"de": 2, "en": 2})

    def test_single_result_is_not_biased_to_first_selected_catalog(self):
        rows = [
            self.row("de", "de1", 80, "A"),
            self.row("en", "en1", 100, "B"),
        ]
        chosen = self.module.select_catalog_balanced(rows, 1, ["de", "en"])
        self.assertEqual(chosen[0]["todayCatalogLanguage"], "en")

    def test_duplicate_logical_recipe_is_never_emitted_twice_for_language_quota(self):
        rows = [
            self.row("de", "same", 100, "A"),
            self.row("en", "same", 99, "A"),
        ]
        chosen = self.module.select_catalog_balanced(rows, 2, ["de", "en"])
        self.assertEqual(len(chosen), 1)
        self.assertEqual(chosen[0]["groupingFunctionalId"], "same")


if __name__ == "__main__":
    unittest.main()
