from copy import deepcopy
import asyncio
from datetime import datetime
import importlib
import json
from pathlib import Path
import re
import sys
import types
import unittest
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components/cook4me"


class SharedCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = types.ModuleType("cook4me_shared_v63_test")
        package.__path__ = [str(COMPONENT)]
        sys.modules[package.__name__] = package
        cls.release = importlib.import_module(f"{package.__name__}.release_catalog")
        cls.presentation = importlib.import_module(f"{package.__name__}.catalog_presentation")
        cls.filters = importlib.import_module(f"{package.__name__}.shared_recipe_filters")
        cls.payload = cls.release.load_release_catalog()

    def test_assistant_locale_covers_every_source_name_and_merges_display_aliases(self):
        locale = json.loads((COMPONENT / "catalog_ui_locales/el.json").read_text())
        self.assertEqual(len(locale["labels"]), 3713)
        self.assertIn("Assistant-authored", locale["translationSource"])
        rows = self.release.ingredient_choices("el")
        self.assertTrue(all(re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", row["name"]) for row in rows))
        self.assertEqual(len({self.presentation.norm(row["name"]) for row in rows}), len(rows))
        self.assertTrue(all(row["presentationVersion"] == 63 for row in rows))
        self.assertFalse(any(row["name"].startswith("Απροσδιόριστο") for row in rows))
        self.assertLess(len(rows), 3713)
        sources = {row["id"]: row for row in self.payload["ingredients"]}
        for row in rows:
            self.assertIn(row["ingredientId"], row["sourceIngredientIds"])
            self.assertEqual(row.get("key"), sources[row["ingredientId"]].get("key"))
            self.assertNotIn("nutrition", row, "Display merging cannot assign a sibling's nutrient profile")
            for ident in row["sourceIngredientIds"]:
                canonical = self.presentation.name_key(self.presentation.clean_name(sources[ident]["canonicalName"]))
                self.assertIn(canonical, locale["labels"], canonical)
                self.assertNotIn(canonical, locale["excludedNames"])
        for value in ("100% Κρέμα φιστικιού", "Κρέμα γάλακτος 15% λιπαρά"):
            # Food composition must survive name cleanup, independent of word order/case.
            percent = re.search(r"\d+%", value).group()
            self.assertTrue(any(percent in row["name"] for row in rows))

    def row(self, name, *, home=True, protein=10, cost=2, coverage=1, ingredient="rice"):
        return {"title": name, "mealTypes": ["main"], "ingredients": [{"ingredientId": ingredient}],
            "match": {"score": 10, "fullyAvailableByQuantity": home, "quantityShortages": [] if home else [{"key": "rice"}]},
            "nutrition": {"coverage": 1, "totals": {"protein": protein*2}, "perServing": {"protein": protein, "fiber": 3}},
            "cost": {"coverage": coverage, "perServingByCurrency": {"EUR": cost}}}

    def test_stock_ingredient_aliases_and_cost_limits_apply_together(self):
        rows = [self.row("selected", ingredient="rice-sibling"), self.row("no stock", home=False),
            self.row("partial price", coverage=.5), self.row("expensive", cost=8), self.row("different", ingredient="onion")]
        before = deepcopy(rows)
        found = self.filters.apply_filters(rows, {"onlyHome": True, "ingredients": ["k:rice"], "maxCost": 3, "currency": "EUR"}, ingredient_groups={"k:rice": ["rice", "rice-sibling"]})
        self.assertEqual([row["title"] for row in found], ["selected"])
        self.assertEqual(rows, before)

    def test_unknown_cost_or_other_currency_is_not_treated_as_free(self):
        known, unknown, other = self.row("known"), self.row("unknown", cost=None), self.row("other")
        other["cost"]["perServingByCurrency"] = {"USD": 1}
        found = self.filters.apply_filters([known, unknown, other], {"maxCost": 3, "currency": "EUR"})
        self.assertEqual([row["title"] for row in found], ["known"])

    def test_targets_rank_known_values_without_fabricating_missing_nutrients(self):
        distant, close, unknown = self.row("distant", protein=5), self.row("close", protein=29), self.row("unknown")
        unknown["nutrition"] = {}
        found = self.filters.apply_filters([distant, unknown, close], {"proteinTarget": 30})
        self.assertEqual(found[0]["title"], "close")
        self.assertEqual(next(row for row in found if row["title"] == "unknown")["nutrition"], {})
        self.assertIsNone(self.filters.normalize_filters({"maxCost": "nan"})["maxCost"])

    def test_real_offline_filtering_precedes_pagination_and_preserves_families(self):
        def process(rows):
            for row in rows:
                row["cost"] = {"coverage": 1, "perServingByCurrency": {"EUR": 2}}
            return self.filters.apply_filters(rows, {"maxCost": 3, "proteinTarget": 15})
        kwargs = dict(language="el", configured_language="de", country="DE", catalog_languages=["de"], group_families=True, filter_rows=process, diet="omnivore", size=2)
        all_rows = self.release.search_release_recipes("risotto", **kwargs, all_results=True)["items"]
        first = self.release.search_release_recipes("risotto", **kwargs)
        second = self.release.search_release_recipes("risotto", **kwargs, page=1)
        self.assertGreater(len(all_rows), 2)
        self.assertEqual(first["page"]["totalElements"], len(all_rows))
        self.assertEqual(first["items"]+second["items"], all_rows[:4])
        self.assertEqual(len({r["displayFamilyId"] for r in all_rows}), len(all_rows))
        self.assertTrue(all(row["safety"]["strictlyAllowed"] for row in all_rows))

    def test_runtime_ranks_all_candidates_before_stock_and_ingredient_filters(self):
        prefix = "cook4me_shared_runtime_v63_test"
        package = types.ModuleType(prefix)
        package.__path__ = [str(COMPONENT)]
        identity = lambda value: value
        ws = types.SimpleNamespace(websocket_command=lambda _: identity, async_response=identity)
        modules = {
            prefix: package,
            "homeassistant.core": types.SimpleNamespace(HomeAssistant=object, callback=identity),
            "homeassistant.components": types.SimpleNamespace(websocket_api=ws),
            "homeassistant.helpers.storage": types.SimpleNamespace(Store=object),
            "homeassistant.util": types.SimpleNamespace(dt=types.SimpleNamespace(now=datetime.now)),
            "voluptuous": types.SimpleNamespace(Required=lambda value, **_: value, Optional=lambda value, **_: value, All=lambda *args: None, In=lambda _: None, Coerce=lambda _: None, Range=lambda **kwargs: None),
            f"{prefix}.websocket": types.SimpleNamespace(),
            f"{prefix}.websocket_v10": types.SimpleNamespace(),
            f"{prefix}.websocket_v18": types.SimpleNamespace(_recent_identities=lambda *args, **kwargs: set()),
        }
        async def run():
            async def executor(function, *args):
                return function(*args)
            stock = [{"key": key, "name": key.title(), "quantity": 1000, "unit": "g"} for key in ("rice", "onion")]
            bridge = types.SimpleNamespace(hass=types.SimpleNamespace(async_add_executor_job=executor),
                recipe_hub=types.SimpleNamespace(profile={"diet": "omnivore", "houseIngredients": stock}, habit_terms=[]),
                _nutrition_store=types.SimpleNamespace(generic={}, stock_lots={}), _meal_history_store=types.SimpleNamespace(recent=lambda _: []))
            runtime = importlib.import_module(f"{prefix}.shared_recipe_runtime")
            rows = [{"title": f"Recipe {index}", "ingredients": [{"ingredientId": "rice" if index == 59 else "onion", "foodKey": "rice" if index == 59 else "onion", "foodName": "Rice" if index == 59 else "Onion", "quantity": 100, "unit": "g"}]} for index in range(60)]
            with patch.object(runtime, "ingredient_aliases", return_value={}):
                process = await runtime.processor(bridge, {"onlyHome": True, "ingredients": ["k:rice"]})
                found = process(rows)
            self.assertEqual([row["title"] for row in found], ["Recipe 59"])
            self.assertTrue(found[0]["match"]["fullyAvailableByQuantity"])
        with patch.dict(sys.modules, modules):
            asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
