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
        self.assertEqual(len([p for p in data["profiles"].values() if p["seasonality"]["status"] == "reviewed"]), 71)
        self.assertEqual(len([p for p in data["profiles"].values() if p["afterOpening"].get("rules")]), 14)

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
        for name in ("Potato starch", "Sweet potato", "Small cooked potatoes (for serving)"):
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
