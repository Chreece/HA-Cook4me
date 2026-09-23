"""Price-audit regressions with no network or Home Assistant installation.

Execute production functions via AST; isolate storage, stock allocation and
catalog I/O. This is a unit suite, not a live retailer or HA end-to-end test.
"""
from __future__ import annotations

import ast
import asyncio
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"


def load_source(name, injected=None, selected=None):
    path = COMPONENT / (name + ".py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.level or (node.module or "").startswith("homeassistant")):
            continue
        if selected is not None and not isinstance(node, (ast.Import, ast.ImportFrom)):
            names = {getattr(node, "name", "")}
            if isinstance(node, ast.Assign):
                names |= {target.id for target in node.targets if isinstance(target, ast.Name)}
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                names.add(node.target.id)
            if not names & selected:
                continue
        nodes.append(node)
    namespace = {"__name__": "cook4me_price_audit_" + name, "__file__": str(path), **(injected or {})}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


INV = load_source("inventory", selected={
    "_text", "_norm_name", "inventory_identity", "ingredient_identities",
    "_quantity", "_unit_token", "_UNIT_SCALE", "convert_amount",
})
COST = load_source("costs", {"convert_amount": INV["convert_amount"]}, selected={
    "_text", "_number", "_currency", "_country", "_cost_for_amount", "_rounded_currency",
})
UNITS = load_source("price_units")
MEASUREMENTS = load_source("price_measurements", {
    "price_ingredient": UNITS["price_ingredient"],
    "convert_amount": INV["convert_amount"],
    "pricing_name": lambda item: str(item.get("canonicalName") or item.get("name") or "").strip().casefold(),
})
# No portion file or density assumption is needed for these explicit units.
MEASUREMENTS["_portions"] = lambda: {}
MEASUREMENTS["_densities"] = lambda: {}
LOCKS = load_source("store_helpers")


class ReferenceStore:
    def __init__(self, refs=()):
        self.settings = {"country": "DE", "currency": "EUR", "autoGlobalPrices": True}
        self._data = {"references": {str(index): deepcopy(ref) for index, ref in enumerate(refs)}}
        self.calls = []

    def best_reference(self, identity, *, currency="", country="", unit=""):
        self.calls.append((identity, currency, country, unit))
        rows = [row for row in self._data["references"].values() if row.get("identity") == identity]
        if currency:
            rows = [row for row in rows if row.get("currency") == currency]
        if country:
            rows = [row for row in rows if row.get("country") == country]
        if unit:
            rows = [row for row in rows if INV["convert_amount"](1, unit, row.get("basisUnit")) is not None]
        return deepcopy(rows[-1]) if rows else None


def reference(identity="k:oil", *, amount=2.4, quantity=200, unit="g", currency="EUR"):
    return {"identity": identity, "amount": amount, "basisQuantity": quantity,
            "basisUnit": unit, "currency": currency, "country": "DE", "source": "manual"}


def calculator_namespace():
    return load_source("costing", {
        **{name: COST[name] for name in ("_text", "_number", "_currency", "_country", "_cost_for_amount", "_rounded_currency")},
        "convert_amount": INV["convert_amount"],
        "inventory_identity": INV["inventory_identity"],
        "ingredient_identities": INV["ingredient_identities"],
        "normalize_inventory": deepcopy,
        "allocate_stock": lambda stock, requests: [None for _ in requests],
        "price_options": MEASUREMENTS["price_options"],
        "add_budget_estimates": lambda cost, *args, **kwargs: cost,
        "price_confidence": lambda cost: {},
    })


class MemoryStore:
    loads = 0

    def __init__(self, *args):
        self.data = None

    async def async_load(self):
        type(self).loads += 1
        await asyncio.sleep(0)
        return deepcopy(self.data)

    async def async_save(self, data):
        self.data = deepcopy(data)


class FakeHass:
    def __init__(self):
        self.calculations = 0

    async def async_add_executor_job(self, action):
        self.calculations += 1
        await asyncio.sleep(0)
        return action()


def cache_namespace():
    return load_source("recipe_cost_cache", {
        "Store": MemoryStore, "DOMAIN": "cook4me",
        "inventory_identity": INV["inventory_identity"],
        "ingredient_identities": INV["ingredient_identities"],
        "normalize_inventory": deepcopy,
        "pricing_name": lambda item: str(item.get("canonicalName") or item.get("name") or "").strip().casefold(),
        "store_load_lock": LOCKS["store_load_lock"],
        "calculate_recipe_cost": lambda recipe, *args, **kwargs: {
            "totalsByCurrency": {"EUR": 0.30},
            "ingredients": [{"name": raw.get("name"), "costsByCurrency": {"EUR": 0.30}}
                            for raw in recipe.get("ingredients") or [] if isinstance(raw, dict)],
        },
    })


def recipe():
    return {"servings": 2, "ingredients": [{"key": "recipe-oil", "name": "Σησαμέλαιο",
            "canonicalName": "sesame oil", "quantity": 25, "unit": "g", "identities": ["k:stored-oil"]}]}


def stock():
    return [{"key": "stored-oil", "name": "Oil", "quantity": 100, "unit": "g", "lots": [
        {"id": "bottle", "quantity": 100, "barcode": "123", "bestBefore": "2026-10-01",
         "addedAt": "2026-09-01", "ingredientLinks": []}]}]


class GreekPriceUnitsTests(unittest.TestCase):
    def test_greek_mass_and_volume(self):
        for label, expected in {"γρ": "g", "γρ.": "g", "γραμμάρια": "g", "κιλά": "kg",
                                "κιλό": "kg", "χιλιοστόλιτρα": "ml", "λίτρα": "l", "λίτρο": "l"}.items():
            with self.subTest(label=label):
                self.assertEqual(UNITS["price_ingredient"]({"quantity": 2, "unit": label})["unit"], expected)

    def test_greek_counts(self):
        for label in ("τεμ", "τεμ.", "τεμάχιο", "τεμάχια"):
            with self.subTest(label=label):
                self.assertEqual(UNITS["price_ingredient"]({"quantity": 2, "unit": label})["unit"], "pcs")

    def test_greek_spoons(self):
        for label, expected in {"κ.σ.": "tbsp", "κ. σ.": "tbsp", "κουταλιές της σούπας": "tbsp",
                                "κ.γ.": "tsp", "κ. γ.": "tsp", "κουταλάκια του γλυκού": "tsp"}.items():
            with self.subTest(label=label):
                self.assertEqual(UNITS["price_ingredient"]({"quantity": 2, "unit": label})["unit"], expected)

    def test_unicode_and_case(self):
        label = unicodedata.normalize("NFD", "ΓΡΑΜΜΆΡΙΑ")
        self.assertEqual(UNITS["price_ingredient"]({"quantity": 2, "unit": label})["unit"], "g")

    def test_decimal_comma_in_spoon_measurement(self):
        options = MEASUREMENTS["price_options"]({"name": "sesame oil", "quantity": "1,5", "unit": "κ.σ."})
        volume = next(option for option in options if option["unit"] == "ml")
        self.assertEqual(volume["quantity"], 22.5)
        self.assertEqual(volume["estimate"]["kind"], "spoon_volume")

    def test_decimal_comma_in_native_mass(self):
        options = MEASUREMENTS["price_options"]({"name": "sesame oil", "quantity": "0,25", "unit": "κιλά"})
        self.assertEqual(options[0], {"quantity": 0.25, "unit": "kg"})

    def test_source_recipe_is_not_mutated(self):
        item = {"name": "Oil", "quantity": None, "weight": {"quantity": "1,5", "unit": "γρ."}}
        before = deepcopy(item)
        normalized = UNITS["price_ingredient"](item)
        self.assertEqual(item, before)
        self.assertEqual(normalized["weight"]["unit"], "g")

    def test_stable_provider_id_wins(self):
        item = {"quantity": 25, "unit": "κ.σ.", "unitKey": "UNIT_27"}
        self.assertEqual(UNITS["price_ingredient"](item)["unit"], "g")

    def test_unknown_provider_id_is_not_overridden(self):
        item = {"quantity": 2, "unit": "κ.σ.", "unitKey": "UNIT_UNREVIEWED"}
        self.assertEqual(UNITS["price_ingredient"](item), item)

    def test_ambiguous_labels_remain_unresolved(self):
        for label in ("κουτάλι", "κουταλιά", "πρέζα", "πακέτο", "ματσάκι", "κομμάτι", "φέτα"):
            with self.subTest(label=label):
                self.assertEqual(UNITS["price_ingredient"]({"quantity": 2, "unit": label})["unit"], label)

    def test_invalid_quantities_do_not_become_prices(self):
        for value in (True, False, -1, 0, float("nan"), float("inf"), "1,2,3", None):
            with self.subTest(value=value):
                self.assertEqual(MEASUREMENTS["price_options"]({"name": "Oil", "quantity": value, "unit": "g"}), [])

    def test_existing_german_and_french_spoons(self):
        for label, expected in (("EL", "tbsp"), ("TL", "tsp"), ("c. à s.", "tbsp"), ("c. à c.", "tsp")):
            with self.subTest(label=label):
                self.assertEqual(UNITS["price_ingredient"]({"quantity": 2, "unit": label})["unit"], expected)


class CostCalculationTests(unittest.TestCase):
    def setUp(self):
        self.ns = calculator_namespace()

    def test_known_price_is_proportional_not_package_total(self):
        self.assertAlmostEqual(COST["_cost_for_amount"](reference(), 25, "g"), 0.30)
        self.assertAlmostEqual(COST["_cost_for_amount"](reference(), 0.025, "kg"), 0.30)

    def test_incompatible_units_are_not_water_density(self):
        self.assertIsNone(COST["_cost_for_amount"](reference(), 25, "ml"))

    def test_zero_and_unknown_prices_stay_distinct(self):
        self.assertEqual(COST["_cost_for_amount"](reference(amount=0), 25, "g"), 0)
        self.assertIsNone(COST["_cost_for_amount"](reference(amount=None), 25, "g"))
        self.assertIsNone(COST["_cost_for_amount"](reference(quantity=0), 25, "g"))

    def test_cost_request_preserves_reviewed_identities(self):
        raw = {**recipe()["ingredients"][0], "identity": "k:explicit-oil"}
        result = self.ns["_ingredient"](raw)
        self.assertIn("k:stored-oil", result.get("identities", []))
        self.assertEqual(result.get("identity"), "k:explicit-oil")
        result["identities"].append("k:changed")
        self.assertNotIn("k:changed", raw["identities"])

    def test_exact_purchase_keeps_paid_currency(self):
        store = ReferenceStore([reference("lot:bottle", currency="USD")])
        result, kind = self.ns["_lot_reference"](store, {"id": "bottle"}, currency="EUR", country="DE", unit="g")
        self.assertEqual(result["currency"], "USD")
        self.assertEqual(kind, "exact_purchase")

    def test_incompatible_lot_basis_can_use_compatible_barcode(self):
        store = ReferenceStore([reference("lot:bottle", unit="pcs"), reference("barcode:123")])
        result, kind = self.ns["_lot_reference"](store, {"id": "bottle", "barcode": "123"}, currency="EUR", country="DE", unit="g")
        self.assertEqual(result["identity"], "barcode:123")
        self.assertEqual(kind, "global_barcode_estimate")

    def test_consumption_passes_units_to_barcode_selection(self):
        store = ReferenceStore([reference("barcode:123"), reference("barcode:123", unit="pcs")])
        result = self.ns["calculate_consumption_cost"]({"deductedLots": [{"barcode": "123", "quantity": 25, "unit": "g"}]}, store)
        self.assertEqual(result["totalsByCurrency"], {"EUR": 0.30})
        self.assertTrue(result["estimated"])

    def test_paid_and_estimated_remainder_are_not_double_counted(self):
        paid = reference("lot:bottle", amount=2, quantity=100)
        estimate = reference("k:recipe-oil", amount=4, quantity=100)
        store = ReferenceStore([paid, estimate])
        self.ns["allocate_stock"] = lambda inventory, requests: [{"unit": "g", "lots": [{"id": "bottle", "quantity": 10}]}]
        result = self.ns["calculate_recipe_cost"](recipe(), [], store)
        self.assertEqual(result["totalsByCurrency"], {"EUR": 0.80})
        self.assertEqual(result["perServingByCurrency"], {"EUR": 0.40})
        self.assertEqual(result["exactPurchaseCoverage"], 0.4)
        self.assertTrue(result["estimated"])

    def test_unpriced_ingredient_does_not_turn_into_zero_total(self):
        result = self.ns["calculate_recipe_cost"](recipe(), [], ReferenceStore())
        self.assertEqual(result["totalsByCurrency"], {})
        self.assertFalse(result["complete"])
        self.assertEqual(result["missingIngredientCount"], 1)

    def test_empty_consumption_report_is_safe(self):
        for report in ({}, {"deductedLots": None}, None):
            with self.subTest(report=report):
                result = self.ns["calculate_consumption_cost"](report, ReferenceStore())
                self.assertEqual(result["totalsByCurrency"], {})
                self.assertEqual(result["coverage"], 0)

    def test_zero_package_basis_is_not_usable(self):
        self.ns["lookup_open_prices"] = lambda *args, **kwargs: {"items": [
            {"usable": True, "pricePer": "UNIT", "basisQuantity": 0, "basisUnit": "g"}]}
        result = self.ns["lookup_open_prices_safe"]("123")
        self.assertEqual(result["usableCount"], 0)
        self.assertFalse(result["items"][0]["usable"])

    def test_positive_explicit_package_basis_remains_usable(self):
        self.ns["lookup_open_prices"] = lambda *args, **kwargs: {"items": [
            {"usable": True, "pricePer": "UNIT", "basisQuantity": 200, "basisUnit": "g"}]}
        self.assertEqual(self.ns["lookup_open_prices_safe"]("123")["usableCount"], 1)

    def test_mixed_currencies_are_not_added_together(self):
        store = ReferenceStore([reference("lot:bottle", amount=2, quantity=100, currency="USD"),
                                reference("k:recipe-oil", amount=4, quantity=100)])
        self.ns["allocate_stock"] = lambda inventory, requests: [{"unit": "g", "lots": [{"id": "bottle", "quantity": 10}]}]
        result = self.ns["calculate_recipe_cost"](recipe(), [], store)
        self.assertEqual(result["totalsByCurrency"], {"USD": 0.20, "EUR": 0.60})
        self.assertFalse(result["currencyConversionApplied"])


class PriceFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.ns = cache_namespace()
        self.store = ReferenceStore([reference("lot:bottle")])

    def fingerprint(self, inventory):
        return self.ns["pricing_fingerprint"](recipe(), inventory, self.store)

    def test_reviewed_alias_stock_changes_invalidate_cache(self):
        before = stock()
        after = deepcopy(before)
        after[0]["lots"][0]["quantity"] = 80
        self.assertNotEqual(self.fingerprint(before), self.fingerprint(after))

    def test_link_aliases_are_also_price_evidence(self):
        before = stock()
        before[0]["key"] = "physical-product"
        before[0]["lots"][0]["ingredientLinks"] = [{"key": "other", "identities": ["k:stored-oil"]}]
        after = deepcopy(before)
        after[0]["lots"][0]["quantity"] = 70
        self.assertNotEqual(self.fingerprint(before), self.fingerprint(after))

    def test_paid_reference_change_for_alias_stock_invalidates(self):
        before = self.fingerprint(stock())
        self.store._data["references"]["0"]["amount"] = 3
        self.assertNotEqual(before, self.fingerprint(stock()))

    def test_unrelated_stock_does_not_invalidate(self):
        before = self.fingerprint(stock())
        unrelated = {"key": "unrelated", "unit": "g", "quantity": 999, "lots": []}
        self.assertEqual(before, self.fingerprint(stock() + [unrelated]))

    def test_fefo_metadata_is_included_across_stock_rows(self):
        base = stock()
        # A direct identity isolates the missing FEFO metadata from the alias bug.
        base[0]["key"] = "recipe-oil"
        for field, value in {"bestBefore": "2026-09-25", "openedAt": "2026-09-22", "useWithinDays": 2, "addedAt": "2026-09-02"}.items():
            with self.subTest(field=field):
                changed = deepcopy(base)
                changed[0]["lots"][0][field] = value
                self.assertNotEqual(self.fingerprint(base), self.fingerprint(changed))

    def test_ingredient_id_changes_price_shape(self):
        first = {"ingredients": [{"ingredientId": "first", "name": "Oil", "quantity": 25, "unit": "g"}]}
        second = deepcopy(first)
        second["ingredients"][0]["ingredientId"] = "second"
        self.assertNotEqual(self.ns["_recipe_price_shape"](first), self.ns["_recipe_price_shape"](second))

    def test_quantity_provenance_invalidates_shape(self):
        first = recipe()
        second = deepcopy(first)
        second["ingredients"][0]["priceQuantityEvidence"] = {"kind": "source_recipe_quantity", "sourceUrl": "reviewed-source"}
        self.assertNotEqual(self.ns["_recipe_price_shape"](first), self.ns["_recipe_price_shape"](second))

    def test_string_ingredients_are_not_dropped_from_shape(self):
        self.assertNotEqual(self.ns["_recipe_price_shape"]({"ingredients": ["salt"]}),
                            self.ns["_recipe_price_shape"]({"ingredients": ["pepper"]}))

    def test_servings_change_price_shape(self):
        first = recipe()
        second = deepcopy(first)
        second["servings"] = 4
        self.assertNotEqual(self.ns["_recipe_price_shape"](first), self.ns["_recipe_price_shape"](second))

    def test_country_and_currency_invalidate(self):
        before = self.fingerprint(stock())
        self.store.settings["country"] = "GR"
        self.assertNotEqual(before, self.fingerprint(stock()))
        before = self.fingerprint(stock())
        self.store.settings["currency"] = "USD"
        self.assertNotEqual(before, self.fingerprint(stock()))


class PriceCacheLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ns = cache_namespace()
        self.bridge = SimpleNamespace(hass=FakeHass(), entry=SimpleNamespace(entry_id="audit"))
        self.store = ReferenceStore()
        MemoryStore.loads = 0

    async def test_concurrent_first_access_uses_one_store(self):
        caches = await asyncio.gather(*(self.ns["recipe_cost_cache_for_bridge"](self.bridge) for _ in range(8)))
        self.assertEqual(len({id(cache) for cache in caches}), 1)
        self.assertEqual(MemoryStore.loads, 1)

    async def test_repeated_views_reuse_cached_price(self):
        cache = await self.ns["recipe_cost_cache_for_bridge"](self.bridge)
        first = await cache.async_cost(recipe(), [], self.store)
        second = await cache.async_cost(recipe(), [], self.store)
        self.assertFalse(first["costCacheHit"])
        self.assertTrue(second["costCacheHit"])
        self.assertEqual(self.bridge.hass.calculations, 1)

    async def test_force_refresh_recalculates(self):
        cache = await self.ns["recipe_cost_cache_for_bridge"](self.bridge)
        await cache.async_cost(recipe(), [], self.store)
        result = await cache.async_cost(recipe(), [], self.store, force=True)
        self.assertFalse(result["costCacheHit"])
        self.assertEqual(self.bridge.hass.calculations, 2)

    async def test_translated_names_refresh_without_repricing(self):
        cache = await self.ns["recipe_cost_cache_for_bridge"](self.bridge)
        await cache.async_cost(recipe(), [], self.store)
        translated = recipe()
        translated["ingredients"][0]["name"] = "Sesamöl"
        result = await cache.async_cost(translated, [], self.store)
        self.assertTrue(result["costCacheHit"])
        self.assertEqual(result["ingredients"][0]["name"], "Sesamöl")
        self.assertEqual(self.bridge.hass.calculations, 1)

    async def test_caller_cannot_modify_cached_price(self):
        cache = await self.ns["recipe_cost_cache_for_bridge"](self.bridge)
        result = await cache.async_cost(recipe(), [], self.store)
        result["totalsByCurrency"]["EUR"] = 999
        again = await cache.async_cost(recipe(), [], self.store)
        self.assertEqual(again["totalsByCurrency"]["EUR"], 0.30)

    async def test_prices_reload_from_persistent_storage(self):
        cache = await self.ns["recipe_cost_cache_for_bridge"](self.bridge)
        await cache.async_cost(recipe(), [], self.store)
        cache._loaded = False
        cache._data = {"entries": {}}
        result = await cache.async_cost(recipe(), [], self.store)
        self.assertTrue(result["costCacheHit"])
        self.assertEqual(self.bridge.hass.calculations, 1)


if __name__ == "__main__":
    unittest.main()
