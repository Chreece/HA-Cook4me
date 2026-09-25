from copy import deepcopy
from datetime import date
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components/cook4me"


def module(filename):
    spec = importlib.util.spec_from_file_location("lifecycle_test_" + filename.removesuffix(".py"), COMPONENT / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class LifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lifecycle = module("ingredient_lifecycle.py")
        cls.catalog = module("release_catalog.py")
        cls.inventory = module("inventory.py")

    def profile(self, name):
        payload = {"ingredients": [{"id": "test", "canonicalName": name, "classification": "food"}]}
        self.lifecycle.enrich_catalog_ingredients(payload)
        return self.lifecycle.lifecycle_profile(payload["ingredients"][0])

    def test_bundled_data_has_reviewed_evidence(self):
        data = self.lifecycle.load_lifecycle_data()
        self.lifecycle.validate_lifecycle_data(data)
        self.assertEqual(len([p for p in data["profiles"].values() if p["seasonality"]["status"] == "reviewed"]), 93)
        self.assertEqual(len([p for p in data["profiles"].values() if p["afterOpening"].get("rules")]), 42)

    def test_mint_tarragon_and_lovage_keep_their_regional_harvest_scope(self):
        cases = (
            ("Fresh mint leaves, washed and chopped", [5, 6, 7, 8, 9, 10], "DE-NW"),
            ("Spearmint", [5, 6, 7, 8, 9, 10], "DE-NW"),
            ("Tarragon, washed and chopped", [6, 7, 8, 9], "DE-BY"),
            ("Lovage", [5, 6, 7, 8, 9, 10], "DE-BY"),
        )
        for name, months, region in cases:
            with self.subTest(name=name):
                profile = self.profile(name)
                evidence = profile["seasonality"]["regions"][0]
                self.assertEqual(evidence["sourceRegion"], region)
                self.assertEqual(evidence["basis"], "outdoor_harvest")
                for month in range(1, 13):
                    self.assertEqual(self.lifecycle.seasonal_availability(profile, country="DE", month=month)["status"], "in_season" if month in months else "unknown")
                self.assertEqual(self.lifecycle.seasonal_availability(profile, country="GR", month=months[0])["status"], "unknown")
                self.assertNotIn("rules", profile["afterOpening"])
        for name in ("Dried mint", "Pinch of dried mint", "Frozen mint", "Peppermint essence", "Finely chopped mint and parsley", "Coriander and mint for garnish", "Dried tarragon", "Chopped herbs (tarragon, parsley, chervil, etc.)", "Dried lovage", "Dried lovage (optional)", "Lovage seeds"):
            with self.subTest(excluded=name):
                self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")

    def test_cooking_cream_products_cannot_assign_a_yoghurt_or_other_cream_clock(self):
        codes = ("4104420095205", "4104420241176", "4104420240940")
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura"}
        for code in codes:
            with self.subTest(code=code):
                package = lot | {"barcode": code}
                profile = self.profile("Plant-based cream")
                result = self.lifecycle.opening_window(profile, package, temperature_c=4)
                self.assertEqual((result["daysMin"], result["daysMax"]), (4, 4))
                self.assertEqual(result["consumeBy"], "2026-09-29")
                for name in ("Soy yoghurt", "Plant-based yogurt", "Cream", "Coconut cream", "Coconut milk", "Oat milk", "Soy milk", "Cooking cream or oat cream"):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), package, temperature_c=4))
                soy_result = self.lifecycle.opening_window(self.profile("Soy cream"), package, temperature_c=4)
                self.assertEqual("consumeBy" in soy_result, code == "4104420095205")
                for changes, temp in (({"brand": "Alpro"}, 4), ({"brand": "Other brand"}, 4), ({"barcode": None}, 4), ({"barcode": "4104420262676"}, 4), ({"storage": "pantry"}, 4), ({}, None), ({}, 5)):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, package | changes, temperature_c=temp))
                self.assertEqual(self.lifecycle.opening_window(profile, package | {"useWithinDays": 1})["consumeBy"], "2026-09-26")
        for name in ("Soy cream", "Plant-based cream", "Soy yoghurt", "Plant-based yogurt"):
            # The split preserves the existing Alpro guidance, including its 7 C cap.
            self.assertEqual(self.lifecycle.opening_window(self.profile(name), lot | {"brand": "Alpro"}, temperature_c=7)["consumeBy"], "2026-09-30")
        self.assertNotEqual(self.profile("Soy cream")["profileId"], self.profile("Soy yoghurt")["profileId"])

    def test_olive_barcode_selects_the_package_interval_and_exact_brand_label(self):
        cases = (
            ("4104420211827", 14, "2026-10-09", True),
            ("4104420129849", 5, "2026-09-30", True),
            ("4104420132085", 14, "2026-10-09", True),
            ("42400660", 14, "2026-10-09", True),
            ("40045542", 2, "2026-09-27", False),
        )
        profile = self.profile("Olives")
        lot = {"openedAt": "2026-09-25", "storage": "fridge"}
        for code, days, deadline, origin in cases:
            with self.subTest(code=code):
                for brand in (("Alnatura", "Alnatura Origin") if origin else ("Alnatura",)):
                    for barcode in (code, code.zfill(14)):
                        package = lot | {"brand": brand, "barcode": barcode}
                        result = self.lifecycle.opening_window(profile, package, temperature_c=4)
                        self.assertEqual((result["daysMin"], result["daysMax"]), (days, days))
                        self.assertEqual((result["remindOn"], result["consumeBy"]), (deadline, deadline))
                        self.assertFalse(result["safetyGuarantee"])
                        capped = self.lifecycle.opening_window(profile, package | {"bestBefore": "2026-09-26"}, temperature_c=4)
                        self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-09-26", "2026-09-26"))
                package = lot | {"brand": "Alnatura", "barcode": code}
                for changes, temp in (({"brand": "Other brand"}, 4), ({"brand": "Alnatura Organic"}, 4), ({"brand": ""}, 4), ({"barcode": None}, 4), ({"barcode": code[:-1] + str((int(code[-1]) + 1) % 10)}, 4), ({"storage": "pantry"}, 4), ({}, None), ({}, 5)):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, package | changes, temperature_c=temp))
        # The Origin label belongs to the jar, not the distinct fresh antipasti pack.
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | {"brand": "Alnatura Origin", "barcode": "40045542"}, temperature_c=4))

    def test_olive_colour_and_preparation_do_not_borrow_another_product_rule(self):
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura"}
        cases = (
            ("Pitted green olives, chopped", {"4104420211827": 14, "4104420129849": 5}),
            ("Black olives, sliced into rings", {"4104420132085": 14}),
            ("Green and black olives", {"42400660": 14, "40045542": 2}),
        )
        codes = ("4104420211827", "4104420129849", "4104420132085", "42400660", "40045542")
        for name, expected in cases:
            profile = self.profile(name)
            for code in codes:
                with self.subTest(name=name, code=code):
                    result = self.lifecycle.opening_window(profile, lot | {"barcode": code}, temperature_c=4)
                    self.assertEqual(result.get("daysMax"), expected.get(code))
        for name in ("Olive oil", "Black olive spread", "Pitted Taggiasca olives", "Pitted black olives (or green olives)", "Olives stuffed with almonds"):
            for code in codes:
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), lot | {"barcode": code}, temperature_c=4))

    def test_invalid_evidence_is_rejected(self):
        mutations = [
            lambda d: d["profiles"]["season_asparagus"]["seasonality"]["regions"][0].update(months=[0, 13]),
            lambda d: d["profiles"]["season_asparagus"]["seasonality"]["regions"][0].update(months=[True]),
            lambda d: d["profiles"]["season_asparagus"]["seasonality"]["regions"][0].update(sourceIds=["invented"]),
            lambda d: d["profiles"]["milk"]["afterOpening"]["rules"][0].update(daysMin=7, daysMax=3),
            lambda d: d["profiles"]["milk"]["afterOpening"]["rules"][0].update(daysMin=True),
            lambda d: d["canonicalNames"].update(milk="missing"),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                data = deepcopy(self.lifecycle.load_lifecycle_data())
                mutate(data)
                with self.assertRaises(ValueError):
                    self.lifecycle.validate_lifecycle_data(data)

    def test_preserved_forms_and_ambiguous_rows_never_borrow_fresh_seasons(self):
        for name in ("Frozen strawberries", "Strawberry jam", "Dried tomatoes", "Tomatoes (fresh or canned)", "Milk chocolate", "Milk (cow's milk or plant-based milk)"):
            with self.subTest(name=name):
                self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")
        for classification, unconfirmed in (("ambiguous", False), ("food", True), ("equipment", False)):
            payload = {"ingredients": [{"canonicalName": "Asparagus", "classification": classification, "needsSemanticConfirmation": unconfirmed}]}
            self.lifecycle.enrich_catalog_ingredients(payload)
            self.assertNotIn("lifecycle", payload["ingredients"][0])
        self.assertEqual(self.profile("Canned chopped tomatoes")["seasonality"]["status"], "not_applicable")
        self.assertNotIn("rules", self.profile("Milk powder")["afterOpening"])

    def test_country_month_and_calendar_scope(self):
        profile = self.profile("Asparagus")
        for month in (4, 5, 6):
            self.assertEqual(self.lifecycle.seasonal_availability(profile, country="de", month=month)["status"], "in_season")
        self.assertEqual(self.lifecycle.seasonal_availability(profile, country="GR", month=4)["status"], "unknown")
        # Source is a highlight calendar: omitted months are not a prohibition.
        self.assertEqual(self.lifecycle.seasonal_availability(profile, country="DE", month=12)["status"], "unknown")
        for month in (1, 12):
            self.assertEqual(self.lifecycle.seasonal_availability(self.profile("Kale"), country="DE", month=month)["status"], "in_season")
        self.assertEqual(self.lifecycle.seasonal_availability(self.profile("Button mushrooms"), country="DE", month=2)["status"], "year_round")
        for month in (True, 0, 13, "4", 4.5):
            with self.assertRaises(ValueError):
                self.lifecycle.seasonal_availability(profile, country="DE", month=month)

    def test_canned_range_starts_immediately_and_reminds_at_shorter_end(self):
        lot = {"openedAt": "2028-02-27", "storage": "fridge"}
        saved = deepcopy(lot)
        result = self.lifecycle.opening_window(self.profile("Canned chickpeas"), lot, temperature_c=4)
        self.assertEqual(result["consumeFrom"], "2028-02-27")
        self.assertEqual(result["remindOn"], "2028-03-01")
        self.assertEqual(result["consumeBy"], "2028-03-02")
        self.assertFalse(result["safetyGuarantee"])
        self.assertEqual(lot, saved)

    def test_new_crop_calendars_preserve_regions_and_food_forms(self):
        cases = (
            ("Turnip, peeled and diced", [6, 7, 8, 9, 10, 11], "DE-RP", "outdoor_harvest"),
            ("Snow peas", [6, 7, 8], "DE", "outdoor_harvest"),
            ("Mangetout peas", [6, 7, 8], "DE", "outdoor_harvest"),
            ("Shelled walnuts", [9, 10], "DE", "regional_seasonal_availability"),
            ("Ground hazelnuts", [9, 10, 11], "DE-BY", "regional_seasonal_availability"),
            ("Artichoke", [7, 8, 9, 10], "DE-BY", "regional_seasonal_availability"),
            ("Melon balls", [8, 9], "DE-BY", "regional_seasonal_availability"),
            ("Kiwi", [9, 10], "DE-BY", "regional_seasonal_availability"),
        )
        for name, months, region, basis in cases:
            with self.subTest(name=name):
                profile = self.profile(name)
                evidence = profile["seasonality"]["regions"][0]
                self.assertEqual(evidence["sourceRegion"], region)
                self.assertEqual(evidence["basis"], basis)
                for month in range(1, 13):
                    self.assertEqual(self.lifecycle.seasonal_availability(profile, country="DE", month=month)["status"], "in_season" if month in months else "unknown")
                self.assertEqual(self.lifecycle.seasonal_availability(profile, country="GR", month=months[0])["status"], "unknown")
                self.assertNotIn("rules", profile["afterOpening"])
        for name in ("Turnip greens", "Yellow turnip, cut into 2 cm pieces", "Snow peas, parboiled", "Frozen snow peas", "Walnut oil", "Roasted hazelnuts", "Hazelnut flour", "Hazelnut paste", "Artichoke hearts (fresh or frozen)", "Marinated artichoke hearts", "Frozen artichoke", "Bitter melon, seeds and pith removed, cut 1 cm wide", "Dried kiwi"):
            with self.subTest(excluded=name):
                self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")

    def test_autumn_crops_distinguish_harvest_from_storage_and_other_forms(self):
        cases = (
            ("Peeled sweet chestnuts", [9, 10], "DE-BY", "outdoor_harvest"),
            ("Sweet potato, peeled and diced", [10], "DE-BY", "outdoor_harvest"),
            ("Rutabaga", [1, 2, 3, 4, 9, 10, 11, 12], "DE", "seasonal_calendar_including_stored_produce"),
            ("Swede, peeled and cut into 2 cm-thick pieces", [1, 2, 3, 4, 9, 10, 11, 12], "DE", "seasonal_calendar_including_stored_produce"),
            ("Chanterelles (halved)", [7, 8], "DE", "outdoor_harvest"),
        )
        for name, months, region, basis in cases:
            with self.subTest(name=name):
                profile = self.profile(name)
                evidence = profile["seasonality"]["regions"][0]
                self.assertEqual(evidence["sourceRegion"], region)
                self.assertEqual(evidence["basis"], basis)
                for month in range(1, 13):
                    self.assertEqual(self.lifecycle.seasonal_availability(profile, country="DE", month=month)["status"], "in_season" if month in months else "unknown")
                self.assertEqual(self.lifecycle.seasonal_availability(profile, country="GR", month=months[0])["status"], "unknown")
                self.assertNotIn("rules", profile["afterOpening"])
        for name in ("Cooked chestnuts", "Chestnut flour", "Candied chestnuts", "Chestnut cream", "Chestnut mushrooms, sliced", "Japanese yam", "Kintoki sweet potato, cut 1 cm wide", "Cooked sweet potato", "Sweet potato starch", "Frozen swede", "Yellow turnip, cut into 2 cm pieces", "Canned chanterelles", "Dried chanterelles", "Mushrooms (button mushrooms, porcini, chanterelles)"):
            with self.subTest(excluded=name):
                self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")
        self.assertNotEqual(self.profile("Rutabaga")["profileId"], self.profile("Turnip")["profileId"])
        self.assertNotEqual(self.profile("Sweet potato")["profileId"], self.profile("Potatoes, peeled and diced")["profileId"])

    def test_new_sauces_juice_and_tofu_require_their_own_verified_product(self):
        cases = (
            ("Firm tofu", "4104420094840", 2, 2, "Smoked tofu"),
            ("Smoked tofu", "4104420094864", 2, 2, "Firm tofu"),
            ("Grape juice", "4104420262676", 3, 3, "Grapes"),
            ("Salsa", "42398479", 3, 3, "Passata"),
            ("Curry sauce", "4104420213128", 2, 3, "Curry paste"),
            ("Curry sauce", "4104420212794", 2, 3, "Coconut milk"),
        )
        for name, code, minimum, maximum, other_form in cases:
            with self.subTest(name=name, code=code):
                profile = self.profile(name)
                lot = {"openedAt": "2026-12-30", "brand": "Alnatura", "storage": "fridge", "barcode": code}
                for normalized_code in (code, code.zfill(14)):
                    result = self.lifecycle.opening_window(profile, lot | {"barcode": normalized_code}, temperature_c=4)
                    self.assertEqual(result["consumeFrom"], "2026-12-30")
                    self.assertEqual(result["remindOn"], f"2027-01-0{minimum - 1}")
                    self.assertEqual(result["consumeBy"], f"2027-01-0{maximum - 1}")
                    self.assertFalse(result["safetyGuarantee"])
                capped = self.lifecycle.opening_window(profile, lot | {"bestBefore": "2026-12-31"}, temperature_c=4)
                self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-12-31", "2026-12-31"))
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(other_form), lot, temperature_c=4))
                for changes, temp in (({"barcode": None}, 4), ({"barcode": "4104420231214"}, 4), ({"barcode": code[:-1] + str((int(code[-1]) + 1) % 10)}, 4), ({"brand": "Other brand"}, 4), ({"brand": ""}, 4), ({"storage": "pantry"}, 4), ({}, None), ({}, 5)):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | changes, temperature_c=temp))
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 1})["consumeBy"], "2026-12-31")

    def test_added_tofu_product_rules_preserve_other_manufacturers_conditions(self):
        cases = (
            ("Firm tofu", "Taifun", ("plain_natural_tofu", "covered_with_fresh_water", "water_changed_daily"), 4, "4104420094840"),
            ("Smoked tofu", "Reishunger", ("closed_container",), 2, "4104420094864"),
        )
        for name, brand, conditions, maximum, alnatura_code in cases:
            with self.subTest(brand=brand):
                profile = self.profile(name)
                lot = {"openedAt": "2026-09-24", "brand": brand, "storage": "fridge"}
                for missing in conditions:
                    remaining = tuple(c for c in conditions if c != missing)
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=remaining))
                self.assertEqual(self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=conditions)["daysMax"], maximum)
                # Conflicting barcode/brand evidence cannot use the old rule.
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | {"barcode": alnatura_code}, temperature_c=4, confirmed_conditions=conditions))
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | {"brand": "Alnatura"}, temperature_c=4, confirmed_conditions=conditions))
        for name in ("Silken tofu", "Soft tofu", "Fried tofu"):
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), {"openedAt": "2026-09-24", "brand": "Alnatura", "barcode": "4104420094840", "storage": "fridge"}, temperature_c=4))

    def test_refrigeration_only_sources_do_not_invent_condiment_deadlines(self):
        for name, code in (("Tomato paste", "4104420180918"), ("Ketchup", "4104420031500")):
            with self.subTest(name=name):
                profile = self.profile(name)
                self.assertEqual(profile["afterOpening"]["status"], "label_required")
                self.assertEqual(profile["afterOpening"]["reason"], "no_reviewed_numeric_opening_interval")
                self.assertNotIn("rules", profile["afterOpening"])
                lot = {"openedAt": "2026-09-24", "brand": "Alnatura", "barcode": code, "storage": "fridge"}
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4))
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 2})["consumeBy"], "2026-09-26")
        for name in ("Tomato purée", "Sun-dried tomato paste", "Ketchup (or mustard or burger sauce)", "Ketchup (or passata)"):
            self.assertEqual(self.profile(name)["afterOpening"]["status"], "unknown")

    def test_vegetable_juice_package_selects_its_own_interval(self):
        profile = self.profile("Vegetable juice")
        lot = {"openedAt": "2026-09-24", "brand": "Alnatura", "storage": "fridge"}
        for code, days in (("4104420072862", 3), ("4104420133365", 5)):
            with self.subTest(code=code):
                lot["barcode"] = code
                result = self.lifecycle.opening_window(profile, lot, temperature_c=4)
                self.assertEqual(result["daysMax"], days)
                self.assertEqual(result["consumeBy"], f"2026-09-{24 + days}")
                lot["bestBefore"] = "2026-09-26"
                self.assertEqual(self.lifecycle.opening_window(profile, lot, temperature_c=4)["consumeBy"], "2026-09-26")
                del lot["bestBefore"]
        for code in (None, "4104420231214", "4104420133366"):
            lot["barcode"] = code
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4))

    def test_juice_and_puree_rules_do_not_transfer_to_other_foods(self):
        cases = (
            ("Applesauce", "4104420227408", 3, "Apple compote"),
            ("Apple juice", "4104420208735", 3, "Apple"),
            ("Apple juice", "4104420179677", 3, "Freshly squeezed apple juice"),
            ("Orange juice", "4104420231214", 3, "Fresh orange juice"),
            ("Sauerkraut juice", "4104420072800", 3, "Chopped sauerkraut with juice"),
            ("Beetroot juice", "4104420070202", 5, "Beetroot"),
            ("Lemon juice", "4104420228986", 14, "Freshly squeezed lemon juice"),
            ("Ginger juice", "4104420260467", 14, "Ginger"),
        )
        for name, code, days, other_form in cases:
            with self.subTest(name=name, code=code):
                profile = self.profile(name)
                lot = {"openedAt": "2026-09-24", "brand": "Alnatura", "storage": "fridge", "barcode": code}
                result = self.lifecycle.opening_window(profile, lot, temperature_c=4)
                self.assertEqual(result["daysMax"], days)
                self.assertFalse(result["safetyGuarantee"])
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(other_form), lot, temperature_c=4))
                for changes, temp in (({"brand": "Other brand"}, 4), ({"storage": "pantry"}, 4), ({}, None), ({}, 5)):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | changes, temperature_c=temp))
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 1})["consumeBy"], "2026-09-25")

    def test_earlier_printed_date_caps_both_ends(self):
        result = self.lifecycle.opening_window(self.profile("Canned chopped tomatoes"), {"openedAt": "2026-12-30", "bestBefore": "2027-01-01", "storage": "fridge"}, temperature_c=4)
        self.assertEqual(result["remindOn"], "2027-01-01")
        self.assertEqual(result["consumeBy"], "2027-01-01")

    def test_package_value_wins_and_matches_existing_inventory(self):
        lot = {"openedAt": "2026-09-24", "bestBefore": "2026-10-30", "useWithinDays": "2"}
        result = self.lifecycle.opening_window(self.profile("Milk"), lot)
        self.assertEqual(result["consumeBy"], self.inventory._effective_best_before(lot))
        self.assertEqual(result["kind"], "package_value")
        self.assertEqual(result["daysMax"], 2)
        # A longer package interval also stays authoritative, not overwritten.
        lot["useWithinDays"] = 5
        self.assertEqual(self.lifecycle.opening_window(self.profile("Milk"), lot)["daysMax"], 5)

    def test_unopened_package_has_no_running_clock(self):
        self.assertEqual(self.lifecycle.opening_window(self.profile("Milk"), {"useWithinDays": 3}), {"status": "unopened"})

    def test_storage_and_temperature_must_match(self):
        for storage, temp in (("freezer", -18), ("pantry", 20), ("fridge", 7), ("fridge", None), ("fridge", float("nan")), ("fridge", True)):
            with self.subTest(storage=storage, temp=temp):
                result = self.lifecycle.opening_window(self.profile("Canned corn"), {"openedAt": "2026-09-24", "storage": storage}, temperature_c=temp)
                self.assertEqual(result["status"], "label_required")
                self.assertNotIn("consumeBy", result)

    def test_milk_requires_known_processed_form(self):
        lot = {"openedAt": "2026-09-24", "storage": "fridge"}
        self.assertEqual(self.lifecycle.opening_window(self.profile("Milk"), lot, temperature_c=4)["status"], "label_required")
        result = self.lifecycle.opening_window(self.profile("Milk"), lot, temperature_c=4, confirmed_conditions=("pasteurized_or_uht",))
        self.assertEqual(result["consumeBy"], "2026-09-27")

    def test_manufacturer_guidance_does_not_become_generic(self):
        lot = {"openedAt": "2026-09-24", "storage": "fridge"}
        for brand in ("", "Other brand", "Alpro alternative"):
            lot["brand"] = brand
            self.assertEqual(self.lifecycle.opening_window(self.profile("Soy milk"), lot, temperature_c=4)["status"], "label_required")
        lot["brand"] = "Alpro"
        self.assertEqual(self.lifecycle.opening_window(self.profile("Soy milk"), lot, temperature_c=4)["consumeBy"], "2026-09-29")
        lot["brand"] = "Taifun"
        self.assertEqual(self.lifecycle.opening_window(self.profile("Firm tofu"), lot, temperature_c=4)["status"], "label_required")
        result = self.lifecycle.opening_window(self.profile("Firm tofu"), lot, temperature_c=4, confirmed_conditions=("plain_natural_tofu", "covered_with_fresh_water", "water_changed_daily"))
        self.assertEqual(result["consumeBy"], "2026-09-28")

    def test_no_universal_duration_for_pesto_and_dry_staples(self):
        for name in ("Pesto alla Genovese", "Salt", "Plain yogurt", "Coconut cream"):
            profile = self.profile(name)
            self.assertEqual(profile["afterOpening"]["status"], "label_required")
            self.assertNotIn("rules", profile["afterOpening"])

    def test_product_specific_rules_require_brand_and_verified_gtin(self):
        profile = self.profile("Passata")
        lot = {"openedAt": "2026-09-24", "storage": "fridge", "brand": "Alnatura"}
        for code in (None, "", "4104420250346", "4104420031326", 4104420250345, True, "４１０４４２０２５０３４５"):
            with self.subTest(code=code):
                lot["barcode"] = code
                result = self.lifecycle.opening_window(profile, lot, temperature_c=4)
                self.assertEqual(result["status"], "label_required")
                self.assertNotIn("consumeBy", result)
        for code, rule_id in (("4104420250345", "alnatura_passata_carton"), ("04104420250345", "alnatura_passata_carton"), ("40045238", "alnatura_passata_bottle"), ("00000040045238", "alnatura_passata_bottle")):
            lot["barcode"] = code
            result = self.lifecycle.opening_window(profile, lot, temperature_c=4)
            self.assertEqual(result["consumeBy"], "2026-09-27")
            self.assertEqual(result["ruleId"], rule_id)
        lot["brand"] = "Another brand"
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4))
        lot["useWithinDays"] = 1
        self.assertEqual(self.lifecycle.opening_window(profile, lot)["consumeBy"], "2026-09-25")

    def test_product_form_and_handling_stay_separate(self):
        lot = {"openedAt": "2026-09-24", "storage": "fridge", "brand": "Alnatura", "barcode": "4104420031326"}
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Pesto"), lot, temperature_c=4))
        for code, source_id in (("4104420031326", "alnatura_pesto_basilico"), ("4104420257344", "alnatura_pesto_rosso")):
            lot["barcode"] = code
            result = self.lifecycle.opening_window(self.profile("Pesto"), lot, temperature_c=4, confirmed_conditions=("covered_with_oil",))
            self.assertEqual(result["consumeBy"], "2026-09-29")
            self.assertEqual(result["sourceIds"], [source_id, "bfr_cooling"])
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Basil"), lot, temperature_c=4, confirmed_conditions=("covered_with_oil",)))
        for code in ("4104420213593", "4104420213517"):
            lot["barcode"] = code
            self.assertEqual(self.lifecycle.opening_window(self.profile("Tomato sauce"), lot, temperature_c=4)["consumeBy"], "2026-09-26")
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Passata"), lot, temperature_c=4))
        lot["barcode"] = "4104420229761"
        self.assertEqual(self.lifecycle.opening_window(self.profile("Hummus"), lot, temperature_c=4)["consumeBy"], "2026-10-01")
        for storage, temp in (("pantry", 4), ("fridge", 7), ("freezer", -18)):
            lot["storage"] = storage
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Hummus"), lot, temperature_c=temp))

    def test_malformed_bundled_product_scopes_are_rejected(self):
        for codes in ([], "4104420250345", [True], ["00000000"], ["4104420250346"], ["4104420250345", "04104420250345"]):
            with self.subTest(codes=codes):
                data = deepcopy(self.lifecycle.load_lifecycle_data())
                data["profiles"]["alnatura_passata"]["afterOpening"]["rules"][0]["productBarcodes"] = codes
                with self.assertRaises(ValueError):
                    self.lifecycle.validate_lifecycle_data(data)
        data = deepcopy(self.lifecycle.load_lifecycle_data())
        data["profiles"]["alnatura_passata"]["afterOpening"]["rules"][0]["brand"] = ""
        with self.assertRaises(ValueError):
            self.lifecycle.validate_lifecycle_data(data)

    def test_known_canned_product_cannot_fall_back_past_missing_conditions(self):
        profile = self.profile("Canned corn")
        lot = {"openedAt": "2026-09-24", "storage": "fridge", "brand": "Alnatura", "barcode": "4104420234987"}
        saved = deepcopy(profile)
        for brand, barcode, conditions in (
            ("Alnatura", "4104420234987", ()),
            ("Alnatura", "4104420234987", ("transferred_to_container",)),
            ("Alnatura", "", ("transferred_to_nonmetal_container",)),
            ("Alnatura", "4104420230972", ("transferred_to_nonmetal_container",)),
            ("", "4104420234987", ("transferred_to_nonmetal_container",)),
            ("Other brand", "4104420234987", ("transferred_to_nonmetal_container",)),
        ):
            with self.subTest(brand=brand, barcode=barcode, conditions=conditions):
                lot.update(brand=brand, barcode=barcode)
                result = self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=conditions)
                self.assertEqual(result["status"], "label_required")
                self.assertNotIn("consumeBy", result)
        lot.update(brand="Alnatura", barcode="4104420234987")
        result = self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=("transferred_to_nonmetal_container",))
        self.assertEqual(result["consumeBy"], "2026-09-25")
        self.assertEqual(result["kind"], "manufacturer_guidance")
        self.assertEqual(profile, saved)
        lot["useWithinDays"] = "2"
        self.assertEqual(self.lifecycle.opening_window(profile, lot)["consumeBy"], "2026-09-26")

    def test_verified_legume_products_keep_their_own_windows(self):
        products = (
            ("Chickpeas", "4104420230224", "alnatura_chickpeas_jar", 2, ()),
            ("Canned chickpeas", "4104420230972", "alnatura_chickpeas_can", 2, ()),
            ("Kidney beans", "4104420138803", "alnatura_kidney_beans_jar", 2, ()),
            ("Canned red kidney beans", "4104420187894", "alnatura_kidney_beans_can", 3, ("transferred_to_container",)),
            ("White beans", "4104420170179", "alnatura_white_beans_jar", 2, ()),
            ("White beans (canned)", "4104420187979", "alnatura_white_beans_can", 3, ("transferred_to_container",)),
            ("Canned lentils", "4104420187931", "alnatura_lentils_can", 2, ()),
            ("Baked beans", "4104420141162", "alnatura_baked_beans_jar", 2, ()),
            ("Canned corn", "4104420234987", "alnatura_sweetcorn_can", 1, ("transferred_to_nonmetal_container",)),
            ("Canned chopped tomatoes", "4104420234857", "alnatura_tomato_pieces_can", 3, ("transferred_to_container",)),
        )
        for name, barcode, rule_id, days, conditions in products:
            with self.subTest(name=name, rule_id=rule_id):
                profile = self.profile(name)
                lot = {"openedAt": "2026-09-24", "storage": "fridge", "brand": "Alnatura", "barcode": barcode}
                result = self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=conditions)
                self.assertEqual(result["ruleId"], rule_id)
                self.assertEqual(result["daysMin"], days)
                self.assertEqual(result["daysMax"], days)
                self.assertEqual(result["consumeBy"], f"2026-09-{24 + days}")
                self.assertEqual(result["sourceIds"], [rule_id, "bfr_cooling"])
                if conditions:
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4))

    def test_generic_canned_guidance_stays_limited_to_canned_forms(self):
        lot = {"openedAt": "2026-09-24", "storage": "fridge", "brand": "Other brand"}
        for name in ("Canned chickpeas", "Canned corn", "Canned lentils", "White beans (canned)"):
            result = self.lifecycle.opening_window(self.profile(name), lot, temperature_c=4)
            self.assertEqual(result["kind"], "general_guidance")
            self.assertEqual((result["daysMin"], result["daysMax"]), (3, 4))
        for name in ("Chickpeas", "Cooked chickpeas", "Kidney beans", "White beans", "Cooked white beans", "Lentils", "Cooked lentils", "Baked beans", "Dried chickpeas", "Dried white beans", "Chickpeas, soaked for 12 hours and cooked in Cook4Me"):
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), lot, temperature_c=4))
        lot.update(brand="Alnatura", barcode="4104420234857")
        self.assertEqual(self.lifecycle.opening_window(self.profile("Canned chopped tomatoes"), lot, temperature_c=4)["status"], "label_required")
        self.assertNotEqual(self.lifecycle.opening_window(self.profile("Canned pineapple (cut into quarters)"), lot, temperature_c=4).get("ruleId"), "alnatura_tomato_pieces_can")

    def test_reviewed_product_precedence_is_independent_of_rule_order(self):
        profile = self.profile("Canned chickpeas")
        lot = {"openedAt": "2026-09-24", "storage": "fridge", "brand": "Alnatura", "barcode": "4104420230972"}
        # A generic range cannot override a verified product's own instructions.
        generic = next(r for r in profile["afterOpening"]["rules"] if r["kind"] == "general_guidance")
        generic.update(daysMin=1, daysMax=1)
        for reverse in (False, True):
            if reverse:
                profile["afterOpening"]["rules"].reverse()
            result = self.lifecycle.opening_window(profile, lot, temperature_c=4)
            self.assertEqual(result["ruleId"], "alnatura_chickpeas_can")
            self.assertEqual(result["daysMax"], 2)

    def test_new_herbs_use_outdoor_months_and_shallots_keep_regional_scope(self):
        for name in ("Marjoram", "Oregano", "Fresh rosemary sprig", "Sage leaves", "Fresh thyme leaves"):
            result = self.lifecycle.seasonal_availability(self.profile(name), country="DE", month=5)
            self.assertEqual(result["months"], list(range(5, 11)))
            self.assertEqual(result["basis"], "outdoor_harvest")
            self.assertEqual(result["sourceIds"], ["vz_season_calendar"])
            self.assertEqual(self.lifecycle.seasonal_availability(self.profile(name), country="DE", month=4)["status"], "unknown")
        dill = self.profile("Dill, washed and chopped")
        self.assertEqual(self.lifecycle.seasonal_availability(dill, country="DE", month=5)["months"], list(range(5, 10)))
        self.assertEqual(self.lifecycle.seasonal_availability(dill, country="DE", month=10)["status"], "unknown")
        shallot = self.lifecycle.seasonal_availability(self.profile("Shallots, peeled"), country="DE", month=7)
        self.assertEqual(shallot["months"], [7, 8, 9, 10])
        self.assertEqual(shallot["basis"], "regional_seasonal_availability")
        wild = self.lifecycle.seasonal_availability(self.profile("Wild garlic"), country="DE", month=3)
        self.assertEqual(wild["months"], [3, 4, 5])
        self.assertEqual(wild["sourceRegion"], "DE-HE")
        self.assertEqual(self.lifecycle.seasonal_availability(dill, country="GR", month=5)["status"], "unknown")

    def test_new_raw_variants_exclude_mixtures_and_processed_forms(self):
        for name, expected in (("Grated garlic", "season_garlic"), ("Chopped spring onion", "season_spring_onion"), ("Raw corn cobs (husks and silk removed)", "season_sweetcorn"), ("Peeled cherry tomatoes", "season_tomato"), ("Ripe Conference pears", "season_pear"), ("Washed blueberries", "season_blueberry")):
            self.assertEqual(self.profile(name)["profileId"], expected)
        for name in ("Dried thyme", "Dried oregano", "Dried marjoram", "Dill seeds", "Frozen dill", "Thyme and bay leaves", "Fresh thyme and rosemary", "Shallot, chopped and fried", "Shallot, or small onion", "Frozen garlic", "Garlic powder", "Cooked sweet potato", "Cherry tomatoes and basil", "Cultivated mushrooms", "Frozen plums, halved", "Canned corn", "Chopped tomatoes"):
            self.assertNotEqual(self.profile(name)["seasonality"]["status"], "reviewed")

    def test_herbs_and_leafy_crops_keep_their_season_scope(self):
        basil = self.profile("Fresh basil leaves")
        result = self.lifecycle.seasonal_availability(basil, country="DE", month=6)
        self.assertEqual(result["basis"], "outdoor_harvest")
        self.assertEqual(result["months"], [6, 7, 8, 9, 10])
        self.assertEqual(result["status"], "in_season")
        self.assertEqual(self.lifecycle.seasonal_availability(basil, country="DE", month=1)["status"], "unknown")
        for name in ("Parsley, washed and chopped", "Chives", "Chervil", "Sorrel"):
            result = self.lifecycle.seasonal_availability(self.profile(name), country="DE", month=4)
            self.assertEqual(result["status"], "in_season")
            self.assertEqual(result["months"], list(range(4, 11)))
            self.assertEqual(result["basis"], "regional_seasonal_availability")
        for month, status in ((1, "in_season"), (3, "unknown"), (5, "in_season")):
            self.assertEqual(self.lifecycle.seasonal_availability(self.profile("Savoy cabbage"), country="DE", month=month)["status"], status)
        self.assertEqual(self.lifecycle.seasonal_availability(self.profile("Bok choy, chopped"), country="DE", month=5)["months"], list(range(5, 11)))
        self.assertEqual(self.lifecycle.seasonal_availability(basil, country="GR", month=6)["status"], "unknown")
        for name in ("Dried basil", "Thai basil", "Mitsuba (Japanese parsley)", "Garlic chives, cut into 3 cm lengths for finishing", "Boiled Savoy cabbage leaves", "Bean sprouts (or sliced pak choi)", "Chopped herbs (tarragon, parsley, chervil, etc.)", "Frozen spinach", "Cooked bell pepper"):
            self.assertNotEqual(self.profile(name)["seasonality"]["status"], "reviewed")
        self.assertEqual(self.profile("Parsley root")["profileId"], "season_parsley_root")

    def test_oat_drinks_keep_each_manufacturers_own_window(self):
        profile = self.profile("Oat milk")
        lot = {"openedAt": "2026-09-24", "storage": "fridge", "brand": "Alpro"}
        result = self.lifecycle.opening_window(profile, lot, temperature_c=7)
        self.assertEqual((result["daysMin"], result["daysMax"]), (5, 5))
        lot["brand"] = "Oatly"
        conditions = ("package_reclosed_promptly", "opening_not_touched_or_drunk_from")
        for confirmed in ((), conditions[:1], conditions[1:]):
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=confirmed))
        result = self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=conditions)
        self.assertEqual((result["remindOn"], result["consumeBy"]), ("2026-09-29", "2026-10-01"))
        self.assertIn("oatly_opening", result["sourceIds"])
        self.assertNotIn("alpro_opening", result["sourceIds"])
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Soy milk"), lot, temperature_c=4, confirmed_conditions=conditions))
        lot["brand"] = "Other brand"
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=conditions))
        lot["useWithinDays"] = 2
        self.assertEqual(self.lifecycle.opening_window(profile, lot)["consumeBy"], "2026-09-26")

    def test_plant_alternatives_and_reishunger_require_matching_products(self):
        lot = {"openedAt": "2026-09-24", "storage": "fridge", "brand": "Alpro"}
        for name in ("Soy cream", "Plant-based cream", "Soy yoghurt"):
            self.assertEqual(self.lifecycle.opening_window(self.profile(name), lot, temperature_c=7)["consumeBy"], "2026-09-29")
        for name in ("Cream", "Plain yogurt", "Coconut milk"):
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), lot, temperature_c=4))
        lot["brand"] = "Reishunger"
        result = self.lifecycle.opening_window(self.profile("Coconut milk"), lot, temperature_c=4)
        self.assertEqual((result["daysMin"], result["daysMax"]), (2, 3))
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Coconut cream"), lot, temperature_c=4))
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Smoked tofu"), lot, temperature_c=4))
        result = self.lifecycle.opening_window(self.profile("Smoked tofu"), lot, temperature_c=4, confirmed_conditions=("closed_container",))
        self.assertEqual(result["consumeBy"], "2026-09-26")
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Firm tofu"), lot, temperature_c=4, confirmed_conditions=("closed_container",)))

    def test_potato_availability_distinguishes_new_and_stored_crops(self):
        for month in (1, 6, 12):
            result = self.lifecycle.seasonal_availability(self.profile("Potatoes, peeled and diced"), country="DE", month=month)
            self.assertEqual(result["status"], "year_round")
            self.assertEqual(result["sourceIds"], ["bzfe_potatoes"])
            self.assertEqual(result["basis"], "seasonal_calendar_including_stored_produce")
        for month, status in ((1, "unknown"), (6, "in_season"), (7, "in_season"), (12, "unknown")):
            self.assertEqual(self.lifecycle.seasonal_availability(self.profile("New potatoes"), country="DE", month=month)["status"], status)
        for name in ("Potato starch", "Japanese yam", "Small cooked potatoes (for serving)"):
            self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")

    def test_reviewed_cutting_aliases_do_not_enrich_prepared_mixtures(self):
        for name, profile in (("Diced eggplant", "season_aubergine"), ("Grated carrots", "season_carrot"), ("Finely chopped onion", "season_onion"), ("Washed and diced zucchini", "season_courgette"), ("Granny Smith apples", "season_apple")):
            self.assertEqual(self.profile(name)["profileId"], profile)
        for name in ("Peeled and steamed eggplant", "Grated seasoned carrots", "Fresh or frozen baby onions", "Apple compote", "Tomato pulp", "Peeled tomatoes", "Zucchini flowers"):
            self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")

    def test_bad_dates_and_nonintegral_intervals_are_rejected(self):
        for value in (True, 1.5, "1.5", -1, 0, 3651, "nan"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.lifecycle.opening_window({}, {"openedAt": "2026-09-24", "useWithinDays": value})
        for value in ("2026-02-30", "20260924", "2026-09-24T12:00:00", "garbage"):
            with self.assertRaises(ValueError):
                self.lifecycle.opening_window({}, {"openedAt": value, "useWithinDays": 3})
        with self.assertRaises(ValueError):
            self.lifecycle.opening_window({}, {"openedAt": "9999-12-31", "useWithinDays": 3})

    def test_no_expiry_only_suppresses_printed_date(self):
        lot = {"openedAt": "2026-09-24", "useWithinDays": 3, "bestBefore": "2026-09-25", "noExpiry": True}
        self.assertEqual(self.lifecycle.opening_window({}, lot)["consumeBy"], "2026-09-27")

    def test_exact_identity_resolution_and_localized_choice_surfaces(self):
        row = {"id": "fresh", "key": "M_FOOD_FRESH", "canonicalName": "Asparagus", "translations": {"el": "Σπαράγγια"}, "classification": "food", "nutrition": {"untouched": 1}}
        preserved = {"id": "can", "canonicalName": "Canned chopped tomatoes", "classification": "food"}
        payload = {"ingredients": [row, preserved], "_runtimeIngredientById": {"fresh": row, "M_FOOD_FRESH": row, "can": preserved}}
        self.lifecycle.enrich_catalog_ingredients(payload)
        with patch.object(self.catalog, "load_release_catalog", return_value=payload), patch.object(self.catalog._core, "load_release_catalog", return_value=payload):
            profile = self.catalog.ingredient_lifecycle_profile({"key": "M_FOOD_FRESH", "name": "wrong translated name"})
            self.assertEqual(profile["profileId"], "season_asparagus")
            self.assertEqual(self.catalog.ingredient_lifecycle_profile({"name": "Asparagus"})["seasonality"]["status"], "unknown")
            self.assertEqual(self.catalog.ingredient_lifecycle_profile({"id": "missing", "canonicalName": "Asparagus"})["seasonality"]["status"], "unknown")
            rows = self.catalog.ingredient_rows("el")
            self.assertEqual(rows[0]["lifecycle"]["profileId"], "season_asparagus")
            details = self.catalog._core._enrich_display_ingredient(payload, {"ingredientId": "fresh"})
            self.assertEqual(details["lifecycle"]["profileId"], "season_asparagus")
            choices = self.catalog.ingredient_choices("el")
            choice = next(r for r in choices if r["ingredientId"] == "fresh")
            choice["lifecycle"]["seasonality"]["regions"][0]["months"].clear()
            profile["seasonality"]["regions"][0]["months"].clear()
            self.assertEqual(row["lifecycle"]["seasonality"]["regions"][0]["months"], [4, 5, 6])
            self.assertEqual(row["nutrition"], {"untouched": 1})


if __name__ == "__main__":
    unittest.main()
