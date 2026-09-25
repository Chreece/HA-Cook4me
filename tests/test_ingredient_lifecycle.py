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
        self.assertEqual(len([p for p in data["profiles"].values() if p["seasonality"]["status"] == "reviewed"]), 112)
        self.assertEqual(len([p for p in data["profiles"].values() if p["afterOpening"].get("rules")]), 75)

    def test_greek_produce_regions_preserve_german_calendars(self):
        cases = (
            ("Apricot", [5, 6, 7, 8], "Pella, Chalkidiki", [7, 8]),
            ("Sweet cherries", [5, 6, 7, 8], "Pella", [6, 7]),
            ("Peach", [5, 6, 7, 8, 9], "Pella", [7, 8]),
            ("Nectarine", [5, 6, 7, 8, 9], "Pella", [7, 8]),
            ("Yellow peaches (or white peaches or nectarines), peeled and quartered", [5, 6, 7, 8, 9], "Pella", [7, 8]),
            ("Pitted plums, chopped", [7, 8, 9, 10], "Pella", [7, 8, 9]),
            ("Grapes", [7, 8, 9, 10], "Pella, Kavala", [9, 10]),
            ("Green asparagus", [2, 3, 4, 5], "Pella", [4, 5, 6]),
            ("White asparagus", [2, 3, 4, 5], "Pella", [4, 5, 6]),
            ("Kiwi", [1, 2, 3, 4, 5, 10, 11, 12], "Pella, Pieria", [9, 10]),
            ("Peeled sweet chestnuts", [10, 11, 12], "Pella", [9, 10]),
        )
        for name, months, region, german_months in cases:
            with self.subTest(name=name):
                profile = self.profile(name)
                evidence = self.lifecycle.seasonal_availability(profile, country="GR", month=months[0])
                self.assertEqual(evidence["sourceRegion"], region)
                self.assertEqual(evidence["sourceIds"], ["nea_exfrut_calendar", "nea_exfrut_products"])
                self.assertEqual(evidence["months"], months)
                self.assertTrue(evidence["approximate"])
                self.assertEqual(evidence["coverage"], "listed_months_only")
                self.assertEqual(evidence["basis"], "seasonal_calendar_including_stored_produce" if name == "Kiwi" else "regional_seasonal_availability")
                for month in range(1, 13):
                    self.assertEqual(self.lifecycle.seasonal_availability(profile, country="GR", month=month)["status"], "in_season" if month in months else "unknown")
                    self.assertEqual(self.lifecycle.seasonal_availability(profile, country="DE", month=month)["status"], "in_season" if month in german_months else "unknown")
                    self.assertEqual(self.lifecycle.seasonal_availability(profile, country="FR", month=month)["status"], "unknown")
                self.assertNotIn("rules", profile["afterOpening"])

    def test_pomegranate_harvest_does_not_become_stored_or_processed_availability(self):
        profile = self.profile("Pomegranate seeds")
        evidence = profile["seasonality"]["regions"][0]
        self.assertEqual((evidence["sourceRegion"], evidence["basis"]), ("Limni, northern Evia", "outdoor_harvest"))
        self.assertEqual(evidence["sourceIds"], ["elimnion_pomegranate"])
        for month in range(1, 13):
            self.assertEqual(self.lifecycle.seasonal_availability(profile, country="GR", month=month)["status"], "in_season" if month in (10, 11) else "unknown")
            self.assertEqual(self.lifecycle.seasonal_availability(profile, country="DE", month=month)["status"], "unknown")
        for name in ("Pomegranate molasses", "Pomegranate (dried cranberries)", "Pomegranate seeds (or dried cranberries)",
                "Pomegranate juice", "Dried pomegranate seeds", "Frozen plums, halved", "Dried apricots",
                "Apricots in syrup, halved", "Cherries in syrup", "Cooked chestnuts", "Grape seed oil",
                "Fresh or canned grape leaves", "Sour cherries, fresh or frozen"):
            self.assertEqual(self.lifecycle.seasonal_availability(self.profile(name), country="GR", month=10)["status"], "unknown")
        # The sweet-cherry and ordinary-plum source does not review these variants.
        for name in ("Sour cherries", "Mirabelle plums"):
            self.assertEqual(self.lifecycle.seasonal_availability(self.profile(name), country="GR", month=7)["status"], "unknown")

    def test_dmbio_packages_require_exact_identity_and_refrigeration(self):
        cases = (
            ("Canned jackfruit, drained", "4066447443318", "dmbio_jackfruit", 3, 3, "2026-09-28", "2026-09-28"),
            ("Hummus", "4066447910865", "dmbio_hummus_natur", 3, 3, "2026-09-28", "2026-09-28"),
            ("Tomato paste", "4066447887716", "dmbio_tomato_paste", 21, 21, "2026-10-16", "2026-10-16"),
            ("Tomato sauce", "4066447887747", "dmbio_tomato_sauce_350", 1, 2, "2026-09-26", "2026-09-27"),
            ("Tomato sauce", "4066447972153", "dmbio_tomato_sauce_520", 3, 4, "2026-09-28", "2026-09-29"),
        )
        for name, code, rule, minimum, maximum, remind, consume in cases:
            with self.subTest(name=name, code=code):
                profile = self.profile(name)
                lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": " dmBIO ", "barcode": code}
                for barcode in (code, "0" + code):
                    result = self.lifecycle.opening_window(profile, lot | {"barcode": barcode}, temperature_c=4)
                    self.assertEqual(result["ruleId"], rule)
                    self.assertEqual(result["sourceIds"], [rule, "bfr_cooling"])
                    self.assertEqual((result["daysMin"], result["daysMax"]), (minimum, maximum))
                    self.assertEqual((result["remindOn"], result["consumeBy"]), (remind, consume))
                    self.assertFalse(result["safetyGuarantee"])
                for changes, temperature in (({"brand": None}, 4), ({"brand": "Alnatura"}, 4),
                        ({"barcode": None}, 4), ({"barcode": code[:-1] + str((int(code[-1]) + 1) % 10)}, 4),
                        ({"openedAt": None}, 4), ({"storage": "pantry"}, 4), ({"storage": "freezer"}, 4),
                        ({}, None), ({}, 5)):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | changes, temperature_c=temperature))
                capped = self.lifecycle.opening_window(profile, lot | {"bestBefore": "2026-09-25"}, temperature_c=4)
                self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-09-25", "2026-09-25"))
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 1})["consumeBy"], "2026-09-26")
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"noExpiry": True}, temperature_c=4)["consumeBy"], consume)

    def test_dmbio_rules_never_cross_foods_package_forms_or_brands(self):
        scoped = {
            "Canned jackfruit, drained": {"4066447443318"},
            "Houmous": {"4066447910865"}, "Hummus natur": {"4066447910865"},
            "Concentrated tomato purée": {"4066447887716"}, "B- tomato paste": {"4066447887716"},
            "Tomato paste (15 g)": {"4066447887716"}, "Tomato paste (20 g)": {"4066447887716"},
            "Seasoned tomato sauce": {"4066447887747", "4066447972153"},
            "Tomato sauce with basil": {"4066447887747", "4066447972153"},
            "Tomato sauce for pasta": {"4066447887747", "4066447972153"},
        }
        codes = set().union(*scoped.values())
        for name, allowed in scoped.items():
            for code in codes:
                lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "dmBio", "barcode": code}
                self.assertEqual("consumeBy" in self.lifecycle.opening_window(self.profile(name), lot, temperature_c=4), code in allowed)
        for name in ("Tomato paste (jar)", "Tomato purée", "Tomato purée (can)", "Passata", "Tomato", "Ketchup",
                "Chickpeas", "Tahini", "Hummus with beetroot", "Fresh jackfruit", "Jackfruit in syrup"):
            for code in codes:
                lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "dmBio", "barcode": code}
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), lot, temperature_c=4))
        for code, days in (("4104420213593", 2), ("4104420129603", 5)):
            lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura", "barcode": code}
            self.assertEqual(self.lifecycle.opening_window(self.profile("Tomato sauce"), lot, temperature_c=4)["daysMax"], days)
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Tomato sauce"), lot | {"brand": "dmBio"}, temperature_c=4))
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura", "barcode": "4104420229761"}
        self.assertEqual(self.lifecycle.opening_window(self.profile("Hummus"), lot, temperature_c=4)["daysMax"], 7)

    def test_tomato_sauce_package_choice_is_independent_of_rule_order(self):
        profile = self.profile("Tomato sauce")
        for _ in range(2):
            profile["afterOpening"]["rules"].reverse()
            for code, days in (("4066447887747", (1, 2)), ("4066447972153", (3, 4))):
                result = self.lifecycle.opening_window(profile,
                    {"openedAt": "2026-09-25", "storage": "fridge", "brand": "dmBio", "barcode": code}, temperature_c=4)
                self.assertEqual((result["daysMin"], result["daysMax"]), days)

    def test_greek_citrus_calendars_keep_region_and_partial_month_coverage(self):
        cases = (
            (("Lemon", "Fresh lemon, sliced", "Freshly squeezed lemon juice", "Lemon zest",
              "Organic lemon, juiced and zested"), [1, 2, 3, 12], "Western Greece", "bionet_citrus"),
            (("Orange", "Orange, segmented", "Fresh organic orange juice", "Orange zest"),
             [1, 2, 3, 4, 5, 10, 11, 12], "Western Greece", "bionet_citrus"),
            (("Grapefruit", "Grapefruit, peeled and diced"), [1, 2, 3, 11, 12], "Western Greece", "bionet_citrus"),
            (("Mandarin", "Mandarins (zest and segments)", "Small mandarin oranges, peel and white pith removed"),
             [1, 2, 3, 10, 11, 12], "Western Greece", "bionet_citrus"),
            (("Clementine", "Clementines (prepare zest and segments)", "Peeled clementine segments"),
             [1, 12], "Skala, Laconia", "sparta_citrus"),
        )
        for names, months, region, source in cases:
            for name in names:
                with self.subTest(name=name):
                    profile = self.profile(name)
                    evidence = profile["seasonality"]["regions"][0]
                    self.assertEqual(evidence["months"], months)
                    self.assertEqual((evidence["sourceRegion"], evidence["basis"]), (region, "regional_seasonal_availability"))
                    self.assertEqual(evidence["sourceIds"], [source])
                    self.assertTrue(evidence["approximate"])
                    self.assertEqual(evidence["coverage"], "listed_months_only")
                    for month in range(1, 13):
                        result = self.lifecycle.seasonal_availability(profile, country="gr", month=month)
                        self.assertEqual(result["status"], "in_season" if month in months else "unknown")
                        for country in ("DE", "US", "TR"):
                            self.assertEqual(self.lifecycle.seasonal_availability(profile, country=country, month=month)["status"], "unknown")
                    self.assertEqual(profile["afterOpening"]["status"], "unknown")

    def test_citrus_seasons_do_not_cross_varieties_preserves_or_mixtures(self):
        for name in ("Blood oranges", "Organic blood oranges", "Bitter oranges, diced",
                "Fresh bitter orange juice", "Lime (or lemon)", "Lemongrass", "Dried lemon",
                "Candied lemon", "Preserved lemon, diced", "Lemon curd", "Lemon sorbet",
                "Lemon juice (quantity fragment: /2)", "Orange jam", "Orange marmalade",
                "Orange blossom water", "Candied orange peel", "Mandarin honey", "Mandarin liqueur",
                "Avocado, peeled and diced, mixed with lemon juice"):
            with self.subTest(name=name):
                self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")
        for name in ("Lemon juice", "Orange juice"):
            self.assertEqual(self.profile(name)["seasonality"]["status"], "not_applicable")

    def test_philadelphia_original_requires_exact_package_and_prompt_reclosure(self):
        names = ("Cream cheese", "Philadelphia cream cheese", "Fresh cream cheese", "Chopped cream cheese",
            "Cream cheese, cut into bite-size pieces", "Double-cream cream cheese",
            "A - cream cheese (bring to room temperature)", "A- cream cheese, brought to room temperature")
        conditions = ("package_reclosed_promptly",)
        for name in names:
            for code, kind in (("00021000075997", "block"), ("00021000000142", "spread")):
                with self.subTest(name=name, code=code):
                    profile = self.profile(name)
                    lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": " Philadelphia ", "barcode": code}
                    for barcode in (code, code[-12:]):
                        result = self.lifecycle.opening_window(profile, lot | {"barcode": barcode},
                            temperature_c=4, confirmed_conditions=conditions)
                        self.assertEqual(result["ruleId"], "philadelphia_us_original_" + kind)
                        self.assertEqual((result["daysMin"], result["daysMax"]), (10, 10))
                        self.assertEqual((result["remindOn"], result["consumeBy"]), ("2026-10-05", "2026-10-05"))
                        self.assertFalse(result["safetyGuarantee"])
                    for changes, temperature, confirmed in (({}, 4, ()), ({}, 4, ("closed_container",)),
                            ({"barcode": None}, 4, conditions), ({"barcode": "00021000075998"}, 4, conditions),
                            ({"barcode": "00021000083206"}, 4, conditions),
                            ({"brand": None}, 4, conditions), ({"brand": "Other brand"}, 4, conditions),
                            ({"storage": "pantry"}, 4, conditions), ({"storage": "freezer"}, 4, conditions),
                            ({"openedAt": None}, 4, conditions), ({}, None, conditions), ({}, 4.1, conditions)):
                        result = self.lifecycle.opening_window(profile, lot | changes,
                            temperature_c=temperature, confirmed_conditions=confirmed)
                        self.assertNotIn("consumeBy", result)
                    capped = self.lifecycle.opening_window(profile, lot | {"bestBefore": "2026-09-27"},
                        temperature_c=4, confirmed_conditions=conditions)
                    self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-09-27", "2026-09-27"))
                    self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 2})["consumeBy"], "2026-09-27")

    def test_cream_cheese_package_rules_do_not_cross_cheeses_flavours_or_dishes(self):
        for name in ("Herbed cream cheese", "Lučina cream cheese", "Cottage cheese", "Quark",
                "Ricotta", "Mascarpone", "Cream cheese with herbs or plain cheese",
                "Herb cream cheese (or plain)", "Herbed cream cheese (or plain)",
                "Cream cheese frosting", "Vegan cream cheese", "Cheesecake", "Cream"):
            for code in ("00021000075997", "00021000000142"):
                with self.subTest(name=name, code=code):
                    result = self.lifecycle.opening_window(self.profile(name),
                        {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Philadelphia", "barcode": code},
                        temperature_c=4, confirmed_conditions=("package_reclosed_promptly",))
                    self.assertNotIn("consumeBy", result)

    def test_dairy_variants_without_package_evidence_require_label(self):
        for name in ("Cottage cheese", "Portions of cottage cheese", "Chilled cottage cheese portions drained an hour before",
                "Chilled cottage cheese, drained one hour beforehand", "Chilled portions of cottage cheese drained one hour earlier",
                "Cottage cheese with herbs (or plain)", "Fresh brousse cheese or cottage cheese",
                "Cream cheese with herbs or plain cheese", "Herb cream cheese (or plain)", "Herbed cream cheese (or plain)",
                "Full-fat crème fraîche", "Thick crème fraîche", "Thick full-fat crème fraîche",
                "Thick, full-fat crème fraîche", "Crème fraîche (or fresh cheese)"):
            with self.subTest(name=name):
                profile = self.profile(name)
                self.assertEqual(profile["afterOpening"]["status"], "label_required")
                self.assertNotIn("rules", profile["afterOpening"])
                lot = {"openedAt": "2026-09-25", "storage": "fridge"}
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4))
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 3})["consumeBy"], "2026-09-28")

    def test_galbani_cheese_windows_require_brand_and_refrigeration(self):
        cases = (
            (("Ball Mozzarella ball,cut into chunks", "Diced mozzarella", "Grated mozzarella",
              "Grated mozzarella cheese", "Mozzarella", "Mozzarella ball, roughly chopped",
              "Mozzarella slices", "Mozzarella, thickly sliced", "Sliced mozzarella",
              "Small mozzarella balls", "Small mozzarella balls, halved"), 2, "2026-09-27"),
            (("Mascarpone", "Mascarpone cheese", "Drained ricotta", "Ricotta", "Ricotta cheese"), 3, "2026-09-28"),
            (("Gorgonzola", "Gorgonzola cheese"), 5, "2026-09-30"),
        )
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": " Galbani "}
        for names, days, deadline in cases:
            for name in names:
                with self.subTest(name=name):
                    profile = self.profile(name)
                    result = self.lifecycle.opening_window(profile, lot, temperature_c=4)
                    self.assertEqual((result["daysMin"], result["daysMax"]), (days, days))
                    self.assertEqual((result["remindOn"], result["consumeBy"]), (deadline, deadline))
                    self.assertEqual(result["sourceIds"], ["galbani_cheese_opening", "bfr_cooling"])
                    self.assertFalse(result["safetyGuarantee"])
                    for changes, temperature in (({"brand": None}, 4), ({"brand": "Other brand"}, 4),
                            ({"storage": "pantry"}, 4), ({"storage": "freezer"}, 4),
                            ({"openedAt": None}, 4), ({}, None), ({}, 5)):
                        self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | changes, temperature_c=temperature))
                    capped = self.lifecycle.opening_window(profile, lot | {"bestBefore": "2026-09-26"}, temperature_c=4)
                    self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-09-26", "2026-09-26"))
                    self.assertEqual(self.lifecycle.opening_window(profile, lot | {"noExpiry": True}, temperature_c=4)["consumeBy"], deadline)
                    self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 1})["consumeBy"], "2026-09-26")

    def test_cheese_rules_do_not_cross_types_mixtures_or_cooked_forms(self):
        names = ("Ricotta salata", "Spoonfuls of salted ricotta", "Ricotta and spinach tortellini",
            "Gorgonzola (or Roquefort or other blue cheese)",
            "Gorgonzola cheese (or Roquefort or another blue cheese)", "Roquefort", "Dolcelatte",
            "Blue cheese", "Cream cheese", "Quark", "Cottage cheese", "Vegan mozzarella",
            "Smoked mozzarella", "Cooked mozzarella", "Mozzarella and tomato salad",
            "Crema al Mascarpone", "Mascarpone dessert cream", "Homemade ricotta",
            "Feta, diced and marinated in oil", "Oil marinade from feta", "Salad cheese",
            "Grilled halloumi", "Halloumi fries", "Vegan halloumi")
        for name in names:
            with self.subTest(name=name):
                for brand in ("Galbani", "Dodoni"):
                    lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": brand}
                    result = self.lifecycle.opening_window(self.profile(name), lot, temperature_c=4,
                        confirmed_conditions=("vacuum_packed_feta", "feta_in_original_brine", "airtight_container"))
                    self.assertNotIn("consumeBy", result)

    def test_dodoni_feta_requires_confirmation_of_package_form(self):
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "DODONI"}
        for name in ("Chopped feta", "Crumbled feta cheese", "Diced feta cheese", "Feta",
                "Feta cheese", "Plain feta", "Plain feta cheese"):
            with self.subTest(name=name):
                profile = self.profile(name)
                for condition, days, deadline in (("vacuum_packed_feta", 4, "2026-09-29"),
                        ("feta_in_original_brine", 8, "2026-10-03")):
                    for reverse in (False, True):
                        if reverse:
                            profile["afterOpening"]["rules"].reverse()
                        result = self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=(condition,))
                        self.assertEqual((result["daysMin"], result["daysMax"]), (days, days))
                        self.assertEqual((result["remindOn"], result["consumeBy"]), (deadline, deadline))
                    capped = self.lifecycle.opening_window(profile, lot | {"bestBefore": "2026-09-26"},
                        temperature_c=4, confirmed_conditions=(condition,))
                    self.assertEqual(capped["consumeBy"], "2026-09-26")
                    for changes, temperature in (({"brand": None}, 4), ({"brand": "Other brand"}, 4),
                            ({"storage": "pantry"}, 4), ({}, None), ({}, 5)):
                        self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | changes,
                            temperature_c=temperature, confirmed_conditions=(condition,)))
                for conditions in ((), ("covered_with_fresh_water",), ("covered_with_oil",), ("closed_container",)):
                    result = self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=conditions)
                    self.assertEqual(result["status"], "label_required")
                    self.assertNotIn("consumeBy", result)
                # Conflicting confirmations must never extend the shorter window.
                both = self.lifecycle.opening_window(profile, lot, temperature_c=4,
                    confirmed_conditions=("vacuum_packed_feta", "feta_in_original_brine"))
                self.assertEqual(both["consumeBy"], "2026-09-29")
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 2})["consumeBy"], "2026-09-27")

    def test_dodoni_halloumi_requires_airtight_refrigeration(self):
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Dodoni"}
        for name in ("Halloumi", "Halloumi cheese", "Halloumi, sliced"):
            with self.subTest(name=name):
                profile = self.profile(name)
                for temperature in (0, 4, 6):
                    result = self.lifecycle.opening_window(profile, lot, temperature_c=temperature,
                        confirmed_conditions=("airtight_container",))
                    self.assertEqual((result["daysMax"], result["consumeBy"]), (3, "2026-09-28"))
                    self.assertEqual(result["sourceIds"], ["dodoni_cheese_opening"])
                for changes, temperature, conditions in (({}, 4, ()), ({}, 4, ("closed_container",)),
                        ({}, 6.1, ("airtight_container",)), ({}, -1, ("airtight_container",)),
                        ({}, None, ("airtight_container",)), ({"brand": "Other brand"}, 4, ("airtight_container",)),
                        ({"storage": "pantry"}, 4, ("airtight_container",))):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | changes,
                        temperature_c=temperature, confirmed_conditions=conditions))

    def test_millet_flakes_require_exact_package_and_closed_refrigeration(self):
        profile = self.profile("Millet flakes")
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura", "barcode": "4104420013308"}
        for barcode in ("4104420013308", "04104420013308"):
            result = self.lifecycle.opening_window(profile, lot | {"barcode": barcode}, temperature_c=4,
                confirmed_conditions=("closed_container",))
            self.assertEqual((result["daysMin"], result["daysMax"]), (14, 14))
            self.assertEqual((result["remindOn"], result["consumeBy"]), ("2026-10-09", "2026-10-09"))
        for changes, temperature, conditions in (({}, 4, ()), ({"barcode": None}, 4, ("closed_container",)),
                ({"barcode": "4104420013309"}, 4, ("closed_container",)),
                ({"barcode": "4104420266827"}, 4, ("closed_container",)),
                ({"brand": None}, 4, ("closed_container",)), ({"brand": "Other brand"}, 4, ("closed_container",)),
                ({"storage": "pantry"}, 4, ("closed_container",)), ({}, None, ("closed_container",)),
                ({}, 5, ("closed_container",))):
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | changes,
                temperature_c=temperature, confirmed_conditions=conditions))
        for name in ("Millet", "Millet flour", "Millet porridge base:", "Mixed grain flakes", "Muesli", "Oat flakes"):
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), lot, temperature_c=4,
                confirmed_conditions=("closed_container",)))
        capped = self.lifecycle.opening_window(profile, lot | {"bestBefore": "2026-10-01"}, temperature_c=4,
            confirmed_conditions=("closed_container",))
        self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-10-01", "2026-10-01"))

    def test_soy_sauce_vague_months_do_not_become_numeric_days(self):
        for name in ("2 tbsp soy sauce", "[A] Soy sauce", "A- soy sauce", "B- soy sauce (for dressing)",
                "Brewed soy sauce", "C- soy sauce", "Soy sauce", "Soy sauce (for dressing)",
                "Soy sauce (for finishing)", "Soy sauce (for sauce)", "Soy sauce (for seasoning pork)",
                "Soy sauce (seasoning)", "Soy sauce, a little", "Tablespoon of soy sauce", "tbsp soy sauce"):
            with self.subTest(name=name):
                profile = self.profile(name)
                self.assertEqual(profile["afterOpening"]["status"], "label_required")
                self.assertNotIn("rules", profile["afterOpening"])
                for brand in (None, "Kikkoman", "Other brand"):
                    lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": brand}
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4))
                    self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 7})["consumeBy"], "2026-10-02")
        for name in ("Light soy sauce", "Dark soy sauce", "Sweet soy sauce", "Soup soy sauce",
                "Dark soy sauce (tsuyu)", "Soy sauce (quantity fragment: /2 tbsp)",
                "Teriyaki sauce", "Soy sauce and mirin", "Soy beans", "Soy milk"):
            self.assertNotEqual(self.profile(name).get("profileId"), "soy_sauce_label_required")

    def test_bonduelle_canned_vegetables_use_one_day_with_confirmed_handling(self):
        conditions = ("transferred_to_clean_container", "closed_container")
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Bonduelle"}
        for name in ("Canned peas", "Canned mixed beans (110 g)", "Canned green peas, a little",
                "Canned baby carrots, drained", "Canned chickpeas", "Canned red kidney beans",
                "White beans (canned)", "Canned lentils", "Canned sweetcorn"):
            with self.subTest(name=name):
                profile = self.profile(name)
                original = deepcopy(profile)
                for reverse in (False, True):
                    if reverse:
                        profile["afterOpening"]["rules"].reverse()
                    result = self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=conditions)
                    self.assertEqual((result["daysMin"], result["daysMax"]), (1, 1))
                    self.assertEqual((result["remindOn"], result["consumeBy"]), ("2026-09-26", "2026-09-26"))
                    self.assertEqual(result["ruleId"], "bonduelle_canned_vegetables")
                    self.assertFalse(result["safetyGuarantee"])
                capped = self.lifecycle.opening_window(original, lot | {"bestBefore": "2026-09-25"}, temperature_c=4, confirmed_conditions=conditions)
                self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-09-25", "2026-09-25"))
                self.assertEqual(self.lifecycle.opening_window(original, lot | {"useWithinDays": 2})["consumeBy"], "2026-09-27")
                self.assertEqual(self.lifecycle.opening_window(original, lot | {"noExpiry": True}, temperature_c=4, confirmed_conditions=conditions)["consumeBy"], "2026-09-26")

    def test_known_brand_cannot_fall_back_when_its_handling_is_unconfirmed(self):
        conditions = ("transferred_to_clean_container", "closed_container")
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": " bonDUELLE "}
        for name in ("Canned peas", "Canned chickpeas", "Canned red kidney beans",
                "White beans (canned)", "Canned lentils", "Canned sweetcorn"):
            with self.subTest(name=name):
                profile = self.profile(name)
                for confirmed in ((), conditions[:1], conditions[1:], ("transferred_to_container", "closed_container")):
                    result = self.lifecycle.opening_window(profile, lot, temperature_c=4, confirmed_conditions=confirmed)
                    self.assertEqual(result["status"], "label_required")
                    self.assertNotIn("consumeBy", result)
                for changes, temperature in (({}, None), ({}, 5), ({"storage": "pantry"}, 4), ({"storage": "freezer"}, 4), ({"openedAt": None}, 4)):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | changes, temperature_c=temperature, confirmed_conditions=conditions))
                for brand in (None, "Other brand"):
                    generic = self.lifecycle.opening_window(profile, lot | {"brand": brand}, temperature_c=4)
                    self.assertEqual((generic["daysMin"], generic["daysMax"]), (3, 4))
                    self.assertEqual(generic["kind"], "general_guidance")

    def test_bonduelle_rule_does_not_cross_unreviewed_food_forms(self):
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Bonduelle"}
        conditions = ("transferred_to_clean_container", "closed_container")
        for name in ("Peas", "Frozen green peas", "Fresh green beans", "Beans", "Cooked beans",
                "Cooked or canned beans", "Chickpeas", "White beans", "Lentils", "Sweetcorn",
                "Canned tuna", "Canned crab", "Canned creamed corn", "Canned pineapple (cut into quarters)",
                "Canned mixed fruit (190 g), including syrup", "Canned demi-glace sauce", "Fresh salad"):
            with self.subTest(name=name):
                result = self.lifecycle.opening_window(self.profile(name), lot, temperature_c=4, confirmed_conditions=conditions)
                self.assertNotEqual(result.get("ruleId"), "bonduelle_canned_vegetables")
        self.assertEqual(self.profile("Canned tuna")["profileId"], "canned_low_acid")
        self.assertEqual(self.profile("Canned peas")["profileId"], "canned_vegetables")

    def test_exact_product_identity_precedes_brand_family_guidance(self):
        profile = self.profile("Canned chickpeas")
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura", "barcode": "4104420230972"}
        self.assertEqual(self.lifecycle.opening_window(profile, lot, temperature_c=4)["daysMax"], 2)
        for changes in ({"barcode": None}, {"brand": "Bonduelle"}, {"brand": None}):
            result = self.lifecycle.opening_window(profile, lot | changes, temperature_c=4,
                confirmed_conditions=("transferred_to_clean_container", "closed_container"))
            self.assertNotIn("consumeBy", result)
        # Brand guidance has precedence even if generic guidance is shorter.
        profile = deepcopy(self.profile("Canned peas"))
        for rule in profile["afterOpening"]["rules"]:
            if not rule.get("brand"):
                rule.update(daysMin=1, daysMax=1)
            else:
                rule.update(daysMin=2, daysMax=2)
        result = self.lifecycle.opening_window(profile, lot | {"brand": "Bonduelle", "barcode": None},
            temperature_c=4, confirmed_conditions=("transferred_to_clean_container", "closed_container"))
        self.assertEqual((result["daysMax"], result["kind"]), (2, "manufacturer_guidance"))

    def test_mustard_and_mayonnaise_defer_to_package_without_invented_days(self):
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura"}
        for name in ("Mustard", "*Dijon mustard", "English mustard", "B- wholegrain mustard, a little",
                "Tablespoons mustard", "Mayonnaise", "A- mayonnaise (for sauce)", "Vegan mayonnaise"):
            with self.subTest(name=name):
                profile = self.profile(name)
                self.assertEqual(profile["afterOpening"]["status"], "label_required")
                self.assertEqual(profile["seasonality"]["status"], "not_applicable")
                for code in (None, "4104420209152", "4104420028166", "4104420206571"):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | {"barcode": code}, temperature_c=4))
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 7})["consumeBy"], "2026-10-02")
        for name in ("Mustard seed", "White mustard seeds", "Whole white mustard seeds",
                "Mustard and fresh cream for serving", "Ketchup (or mustard or burger sauce)",
                "Cucumbers in mustard brine", "Homemade mayonnaise"):
            with self.subTest(excluded=name):
                self.assertNotIn(self.profile(name).get("profileId"), ("mustard_label_required", "mayonnaise_label_required"))

    def test_dairy_variants_preserve_label_and_pasteurization_requirements(self):
        lot = {"openedAt": "2026-09-25", "storage": "fridge"}
        for name in ("30% whipping cream", "Liquid cream, 15% fat", "Full-fat sour cream",
                "Herbed cream cheese",
                "Greek yoghurt", "Yogurt (125 g cup measure)", "Vanilla yogurt"):
            with self.subTest(name=name):
                profile = self.profile(name)
                self.assertEqual(profile["afterOpening"]["status"], "label_required")
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4))
        for name in ("A- milk", "B- milk", "B- milk, brought to room temperature"):
            with self.subTest(name=name):
                profile = self.profile(name)
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4))
                self.assertEqual(self.lifecycle.opening_window(profile, lot, temperature_c=4,
                    confirmed_conditions=("pasteurized_or_uht",))["consumeBy"], "2026-09-28")
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | {"storage": "pantry"},
                    temperature_c=4, confirmed_conditions=("pasteurized_or_uht",)))
        for name in ("Cooking cream or oat cream", "Low-fat cream (or milk)", "Thick cream or natural yogurt",
                "Oil, mixed with yogurt", "Milk (dairy or non-dairy)"):
            self.assertNotIn(self.profile(name).get("profileId"), ("milk", "label_required"))

    def test_summer_purslane_keeps_species_and_season_boundaries(self):
        for name in ("Purslane", "Summer purslane"):
            profile = self.profile(name)
            evidence = profile["seasonality"]["regions"][0]
            self.assertEqual(evidence["sourceIds"], ["bzfe_summer_purslane"])
            self.assertEqual((evidence["sourceRegion"], evidence["basis"]), ("DE", "regional_seasonal_availability"))
            self.assertTrue(evidence["approximate"])
            for month in range(1, 13):
                self.assertEqual(self.lifecycle.seasonal_availability(profile, country="DE", month=month)["status"],
                    "in_season" if month in (5, 6, 7, 8, 9) else "unknown")
            self.assertEqual(self.lifecycle.seasonal_availability(profile, country="TR", month=6)["status"], "unknown")
            self.assertNotIn("rules", profile["afterOpening"])
        for name in ("Winter purslane", "Postelein", "Miner's lettuce", "Pickled purslane", "Dried purslane",
                "Purslane and spinach", "Cooked purslane"):
            self.assertNotEqual(self.profile(name)["seasonality"]["status"], "reviewed")

    def test_fresh_ginger_and_figs_keep_regional_harvest_scope(self):
        for name, months, region, basis, source in (
            ("Fresh ginger, grated", [10, 11, 12], "DE-NI", "regional_seasonal_availability", "stoevesandt_ginger"),
            ("Ginger, washed well and julienned with the skin on", [10, 11, 12], "DE-NI", "regional_seasonal_availability", "stoevesandt_ginger"),
            ("Figs, cut into eighths", [8, 9, 10], "DE-BY", "outdoor_harvest", "lwg_figs"),
        ):
            with self.subTest(name=name):
                profile = self.profile(name)
                evidence = profile["seasonality"]["regions"][0]
                self.assertEqual((evidence["sourceRegion"], evidence["basis"]), (region, basis))
                self.assertEqual(evidence["sourceIds"], [source])
                self.assertTrue(evidence["approximate"])
                for month in range(1, 13):
                    result = self.lifecycle.seasonal_availability(profile, country="DE", month=month)
                    self.assertEqual(result["status"], "in_season" if month in months else "unknown")
                self.assertEqual(self.lifecycle.seasonal_availability(profile, country="GR", month=10)["status"], "unknown")
                self.assertNotIn("rules", profile["afterOpening"])

    def test_preserved_ginger_and_figs_do_not_receive_fresh_seasons(self):
        for name in (
            "Ginger paste", "Garlic and ginger paste", "Pickled ginger", "Crystallized ginger",
            "Ground ginger", "Dried ginger", "Ginger juice", "Gingerbread spice",
            "Grated ginger", "B- grated ginger", "Minced ginger", "Grated ginger (for sauce)",
            "Frozen fresh ginger", "Dried figs", "Chopped dried figs", "Fig jam", "Figs in syrup",
        ):
            with self.subTest(name=name):
                self.assertNotEqual(self.profile(name)["seasonality"]["status"], "reviewed")

    def test_nine_drink_and_tomato_packages_require_identity_and_cooling(self):
        cases = (
            ("Soy milk", "4104420266827", 3, "2026-09-28"),
            ("Rice milk", "4104420260337", 4, "2026-09-29"),
            ("Oat milk", "4104420186279", 3, "2026-09-28"),
            ("Oat drink", "4104420260139", 3, "2026-09-28"),
            ("Hazelnut milk", "4104420237292", 4, "2026-09-29"),
            ("Cashew milk", "4104420234383", 4, "2026-09-29"),
            ("Coconut drink", "4104420204225", 3, "2026-09-28"),
            ("Sun-dried tomatoes in oil", "42271017", 5, "2026-09-30"),
            ("Sun-dried tomatoes", "40045528", 2, "2026-09-27"),
        )
        for name, code, days, deadline in cases:
            with self.subTest(name=name, code=code):
                profile = self.profile(name)
                lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura", "barcode": code}
                self.assertEqual(profile["seasonality"]["status"], "not_applicable")
                for barcode in (code, code.zfill(14)):
                    result = self.lifecycle.opening_window(profile, lot | {"barcode": barcode}, temperature_c=4)
                    self.assertEqual((result["daysMin"], result["daysMax"]), (days, days))
                    self.assertEqual((result["remindOn"], result["consumeBy"]), (deadline, deadline))
                    self.assertFalse(result["safetyGuarantee"])
                for changes, temperature in (({"barcode": None}, 4), ({"brand": None}, 4),
                        ({"brand": "Other brand"}, 4), ({"openedAt": None}, 4),
                        ({"barcode": code[:-1] + str((int(code[-1]) + 1) % 10)}, 4),
                        ({"storage": "pantry"}, 4), ({"storage": "freezer"}, 4), ({}, None), ({}, 5)):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | changes, temperature_c=temperature))
                capped = self.lifecycle.opening_window(profile, lot | {"bestBefore": "2026-09-26"}, temperature_c=4)
                self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-09-26", "2026-09-26"))
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 1})["consumeBy"], "2026-09-26")

    def test_drink_barcodes_cannot_cross_food_types_or_cooking_forms(self):
        groups = (
            ("Soy milk", {"4104420266827": 3}),
            ("A- unsweetened soy milk", {"4104420266827": 3}),
            ("Soy milk, room temperature", {"4104420266827": 3}),
            ("Rice milk", {"4104420260337": 4}),
            ("Oat milk", {"4104420186279": 3, "4104420260139": 3}),
            ("Hazelnut milk (from organic food stores)", {"4104420237292": 4}),
            ("Cashew drink", {"4104420234383": 4}),
            ("Unsweetened coconut drink", {"4104420204225": 3}),
        )
        codes = set().union(*(set(allowed) for _, allowed in groups))
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura"}
        for name, allowed in groups:
            for code in codes:
                with self.subTest(name=name, code=code):
                    result = self.lifecycle.opening_window(self.profile(name), lot | {"barcode": code}, temperature_c=4)
                    self.assertEqual("consumeBy" in result, code in allowed)
                    if code in allowed:
                        self.assertEqual(result["daysMax"], allowed[code])
                        generic = self.lifecycle.opening_window(self.profile("Plant-based drink"), lot | {"barcode": code}, temperature_c=4)
                        self.assertEqual(generic["consumeBy"], result["consumeBy"])
        for name in ("Almond milk", "Almond drink", "Coconut milk", "Coconut cream", "Coconut water",
                "Soy cream", "Oat cream", "Plant-based cream", "Soy yoghurt", "Milk", "Soy beans",
                "Sweetened soy milk", "Vanilla soy milk", "Homemade oat milk", "Rice and almond drink"):
            for code in codes:
                with self.subTest(excluded=name, code=code):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), lot | {"barcode": code}, temperature_c=4))
        # The recipe's serving-temperature qualifier does not waive cold storage.
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Soy milk, room temperature"),
            lot | {"barcode": "4104420266827", "storage": "pantry"}, temperature_c=4))
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile("Soy milk"),
            lot | {"barcode": "4104420094987"}, temperature_c=4))

    def test_drink_profile_split_preserves_alpro_and_tomato_product_scope(self):
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alpro"}
        for name in ("Soy milk", "Unsweetened soy milk", "Rice milk", "Hazelnut milk", "Almond milk", "Plant milk"):
            with self.subTest(name=name):
                self.assertEqual(self.lifecycle.opening_window(self.profile(name), lot, temperature_c=7)["consumeBy"], "2026-09-30")
        profile = self.profile("Dried tomatoes")
        lot["brand"] = "Alnatura Origin"
        self.assertEqual(self.lifecycle.opening_window(profile, lot | {"barcode": "42271017"}, temperature_c=4)["consumeBy"], "2026-09-30")
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | {"barcode": "40045528"}, temperature_c=4))
        lot["brand"] = "Alnatura"
        # The dry Soft-Tomaten pouch has different storage instructions.
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | {"barcode": "4104420178458"}, temperature_c=4))
        for name in ("Tomato", "Roasted tomatoes", "Tomato paste", "Sun-dried tomato paste", "Sun-dried tomato oil",
                "Tomato powder", "Dry-packed sun-dried tomatoes", "Sun-dried tomatoes and olives"):
            for code in ("42271017", "40045528"):
                with self.subTest(excluded=name, code=code):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), lot | {"barcode": code}, temperature_c=4))

    def test_chili_and_romaine_seasons_keep_source_scope_and_month_boundaries(self):
        cases = (
            ("Fresh chopped chili pepper", [8, 9, 10], "regional_seasonal_availability", "dehner_chili"),
            ("Fresh jalapeño peppers", [8, 9, 10], "regional_seasonal_availability", "dehner_chili"),
            ("Small hot red chili pepper, deseeded", [8, 9, 10], "regional_seasonal_availability", "dehner_chili"),
            ("Romaine lettuce", [5, 6, 7, 8, 9, 10, 11], "outdoor_harvest", "bzfe_romaine"),
            ("Little Gem lettuce", [5, 6, 7, 8, 9, 10, 11], "outdoor_harvest", "bzfe_romaine"),
        )
        for name, months, basis, source in cases:
            with self.subTest(name=name):
                profile = self.profile(name)
                region = profile["seasonality"]["regions"][0]
                self.assertEqual((region["sourceRegion"], region["basis"]), ("DE", basis))
                self.assertEqual(region["sourceIds"], [source])
                self.assertTrue(region["approximate"])
                for month in range(1, 13):
                    result = self.lifecycle.seasonal_availability(profile, country="DE", month=month)
                    self.assertEqual(result["status"], "in_season" if month in months else "unknown")
                self.assertEqual(self.lifecycle.seasonal_availability(profile, country="GR", month=9)["status"], "unknown")
                self.assertNotIn("rules", profile["afterOpening"])

    def test_ambiguous_translated_chilies_and_prepared_forms_do_not_inherit_fresh_seasons(self):
        for name in (
            "Chili", "Chili pepper", "Red chili pepper", "Red chili pepper (seeds removed)",
            "A- red chili, deseeded and finely chopped", "Sliced red chili pepper",
            "Pinch of chili pepper", "Bird's eye chili powder", "Dried chili pepper (takanotsume)",
            "Frozen fresh chili pepper", "Chili flakes", "Chili paste", "Chili in oil",
            "Sweet chili sauce", "Pepperoni", "Red and green chili peppers",
            "Pickled jalapeños", "Fresh or dried chili", "Cooked Romaine lettuce",
            "Romaine and iceberg lettuce", "Little Gem salad with dressing",
        ):
            with self.subTest(excluded=name):
                self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")

    def test_seven_new_packages_require_identity_cooling_and_opening_date(self):
        cases = (
            ("Carrot juice", "4104420221970", 3, "2026-09-28"),
            ("Carrot juice", "4104420070189", 5, "2026-09-30"),
            ("Carrot juice", "4104420072848", 3, "2026-09-28"),
            ("Beetroot juice", "4104420261136", 3, "2026-09-28"),
            ("Beetroot juice", "4104420259980", 3, "2026-09-28"),
            ("Lime juice", "4104420072121", 14, "2026-10-09"),
            ("Canned beetroot with its liquid", "4104420235397", 5, "2026-09-30"),
        )
        for name, code, days, deadline in cases:
            with self.subTest(name=name, code=code):
                profile = self.profile(name)
                lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura", "barcode": code}
                self.assertEqual(profile["seasonality"]["status"], "not_applicable")
                for barcode in (code, code.zfill(14)):
                    result = self.lifecycle.opening_window(profile, lot | {"barcode": barcode}, temperature_c=4)
                    self.assertEqual((result["daysMin"], result["daysMax"]), (days, days))
                    self.assertEqual((result["remindOn"], result["consumeBy"]), (deadline, deadline))
                    self.assertFalse(result["safetyGuarantee"])
                for changes, temperature in (({"barcode": None}, 4), ({"brand": None}, 4),
                        ({"brand": "Other brand"}, 4), ({"barcode": code[:-1] + str((int(code[-1]) + 1) % 10)}, 4),
                        ({"openedAt": None}, 4), ({"storage": "pantry"}, 4), ({"storage": "freezer"}, 4), ({}, None), ({}, 5)):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | changes, temperature_c=temperature))
                capped = self.lifecycle.opening_window(profile, lot | {"bestBefore": "2026-09-26"}, temperature_c=4)
                self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-09-26", "2026-09-26"))
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 1})["consumeBy"], "2026-09-26")

    def test_juice_and_pickled_root_rules_do_not_cross_food_forms(self):
        groups = (
            ("Carrot juice", {"4104420221970": 3, "4104420070189": 5, "4104420072848": 3}),
            ("Beetroot juice", {"4104420261136": 3, "4104420259980": 3, "4104420070202": 5}),
            ("Lime juice", {"4104420072121": 14}),
            ("Pickled beetroot", {"4104420235397": 5}),
        )
        codes = set().union(*(set(codes) for _, codes in groups))
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura"}
        for name, allowed in groups:
            for code in codes:
                with self.subTest(name=name, code=code):
                    result = self.lifecycle.opening_window(self.profile(name), lot | {"barcode": code}, temperature_c=4)
                    self.assertEqual("consumeBy" in result, code in allowed)
                    if code in allowed:
                        self.assertEqual(result["daysMax"], allowed[code])
        for name in (
            "Carrot", "Beetroot", "Cooked beetroot", "Raw beetroot, diced", "Lime",
            "Limes (juice)", "Lime juice and zest (quantity fragment: /2)",
            "Freshly squeezed carrot juice", "Freshly squeezed lime juice", "Beet kvass",
            "Vegetable juice", "Fruit juice", "Carrot and apple juice", "Beetroot and ginger shot",
            "Water combined with beet liquid", "Pickled vegetables (peppers, corn, carrots, mushrooms, peas...)",
        ):
            for code in codes:
                with self.subTest(excluded=name, code=code):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), lot | {"barcode": code}, temperature_c=4))

    def test_reviewed_quantity_fragments_preserve_exact_food_identity(self):
        cases = (
            ("Fresh basil leaves, chopped (quantity fragment: /2 tbsp)", "season_basil"),
            ("Fresh parsley, washed and chopped (quantity fragment: /2 tbsp)", "season_parsley_leaf"),
            ("Fresh thyme leaves (quantity fragment: /4 tsp)", "season_thyme"),
            ("Rosemary sprigs (quantity fragment: /2)", "season_rosemary"),
            ("Chopped onion (quantity fragment: /4)", "season_onion"),
            ("Granny Smith apple, washed and diced (quantity fragment: /4)", "season_apple"),
            ("Small eggplant, washed and diced (quantity fragment: /2)", "season_aubergine"),
            ("g carrots, peeled and cut into pieces", "season_carrot"),
            ("g cauliflower, washed and cut into 2 or 4 parts", "season_cauliflower"),
        )
        for name, ident in cases:
            self.assertEqual(self.profile(name)["profileId"], ident)
        for name in ("Fresh thyme leaves (quantity fragment: /8 tsp)", "Onion, peeled and halved, with clove (quantity fragment: /2)", "Fresh basil or mint (quantity fragment: /2 tbsp)"):
            self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")

    def test_coriander_watercress_lemon_balm_and_romanesco_retain_regional_seasons(self):
        cases = (
            ("Fresh coriander, washed and finely chopped", [5, 6, 7, 8, 9, 10], "DE-NW", "outdoor_harvest", "meinland_coriander"),
            ("Chopped coriander stems", [5, 6, 7, 8, 9, 10], "DE-NW", "outdoor_harvest", "meinland_coriander"),
            ("tbsp coriander leaves, washed and chopped", [5, 6, 7, 8, 9, 10], "DE-NW", "outdoor_harvest", "meinland_coriander"),
            ("Watercress, washed twice (thick stems removed)", [1, 2, 3, 4, 5, 9, 10, 11, 12], "DE-TH", "outdoor_harvest", "kressepark_watercress"),
            ("Lemon balm", [6, 7, 8, 9], "DE-BY", "outdoor_harvest", "lwg_garden_herbs"),
            ("Romanesco broccoli florets", [5, 6, 7, 8, 9, 10], "DE", "regional_seasonal_availability", "iva_romanesco"),
            ("Romanesco cauliflower, washed", [5, 6, 7, 8, 9, 10], "DE", "regional_seasonal_availability", "iva_romanesco"),
        )
        for name, months, region, basis, source in cases:
            with self.subTest(name=name):
                profile = self.profile(name)
                evidence = profile["seasonality"]["regions"][0]
                self.assertEqual((evidence["sourceRegion"], evidence["basis"]), (region, basis))
                self.assertEqual(evidence["sourceIds"], [source])
                self.assertTrue(evidence["approximate"])
                for month in range(1, 13):
                    self.assertEqual(self.lifecycle.seasonal_availability(profile, country="DE", month=month)["status"], "in_season" if month in months else "unknown")
                self.assertEqual(self.lifecycle.seasonal_availability(profile, country="GR", month=months[0])["status"], "unknown")
                self.assertNotIn("rules", profile["afterOpening"])

    def test_fresh_herb_seasons_do_not_transfer_to_seeds_mixtures_or_other_species(self):
        for name in (
            "Coriander", "Coriander (garnish)", "Coriander powder", "Coriander seeds",
            "Ground coriander", "Dried coriander", "Frozen coriander", "Coriander purée",
            "Coriander or parsley, washed and chopped", "Coriander and mint for garnish",
            "Coriander and soybean sprouts", "Vietnamese coriander", "Coriander root",
            "Garden cress", "Watercress (or arugula)", "Frozen watercress", "Watercress soup",
            "Dried lemon balm", "Lemon balm tea", "Frozen lemon balm",
            "Frozen Romanesco broccoli", "Cooked Romanesco", "Romanesco and broccoli",
        ):
            with self.subTest(excluded=name):
                self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")

    def test_coconut_sauerkraut_tomato_juice_and_satay_dates_require_the_package(self):
        cases = (
            ("Coconut milk", "4104420034327", 3),
            ("Coconut milk", "4104420033641", 3),
            ("Sauerkraut", "4104420033849", 5),
            ("Chopped sauerkraut with juice", "4104420033849", 5),
            ("Tomato juice", "4104420072787", 3),
            ("Satay sauce", "4104420257863", 3),
        )
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura"}
        for name, code, days in cases:
            with self.subTest(name=name, code=code):
                profile = self.profile(name)
                package = lot | {"barcode": code}
                self.assertEqual(profile["seasonality"]["status"], "not_applicable")
                for barcode in (code, code.zfill(14)):
                    result = self.lifecycle.opening_window(profile, package | {"barcode": barcode}, temperature_c=4)
                    expected = "2026-09-28" if days == 3 else "2026-09-30"
                    self.assertEqual((result["daysMin"], result["daysMax"]), (days, days))
                    self.assertEqual((result["remindOn"], result["consumeBy"]), (expected, expected))
                    self.assertFalse(result["safetyGuarantee"])
                for changes, temp in (({"brand": "Other brand"}, 4), ({"brand": ""}, 4), ({"barcode": None}, 4), ({"barcode": code[:-1] + str((int(code[-1]) + 1) % 10)}, 4), ({"storage": "pantry"}, 4), ({"openedAt": None}, 4), ({}, None), ({}, 5)):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, package | changes, temperature_c=temp))
                capped = self.lifecycle.opening_window(profile, package | {"bestBefore": "2026-09-26"}, temperature_c=4)
                self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-09-26", "2026-09-26"))
                self.assertEqual(self.lifecycle.opening_window(profile, package | {"useWithinDays": 1})["consumeBy"], "2026-09-26")

    def test_sauce_milk_and_juice_product_rules_stay_with_their_food_form(self):
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura"}
        groups = (
            ("Coconut milk", {"4104420034327", "4104420033641"}),
            ("Sauerkraut", {"4104420033849"}),
            ("Tomato juice", {"4104420072787"}),
            ("Satay sauce", {"4104420257863"}),
        )
        codes = set().union(*(codes for _, codes in groups))
        for name, allowed in groups:
            for code in codes:
                with self.subTest(name=name, code=code):
                    self.assertEqual("consumeBy" in self.lifecycle.opening_window(self.profile(name), lot | {"barcode": code}, temperature_c=4), code in allowed)
        for name in (
            "Coconut cream", "Plant-based cream", "Coconut milk or coconut cream", "Coconut oil",
            "Coconut drink", "Light coconut milk", "Cooked sauerkraut", "Raw sauerkraut",
            "Sauerkraut juice", "White cabbage", "Tomato sauce", "Passata", "Tomato pulp",
            "Vegetable juice", "Freshly squeezed tomato juice", "Satay sauce seasoning",
            "Peanut butter", "Peanuts", "Homemade satay sauce",
        ):
            for code in codes:
                with self.subTest(excluded=name, code=code):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), lot | {"barcode": code}, temperature_c=4))

    def test_coconut_milk_keeps_reishunger_range_without_accepting_conflicting_barcodes(self):
        profile = self.profile("Coconut milk")
        self.assertEqual(profile["profileId"], "reishunger_coconut_milk")
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Reishunger"}
        result = self.lifecycle.opening_window(profile, lot, temperature_c=4)
        self.assertEqual((result["daysMin"], result["daysMax"]), (2, 3))
        self.assertEqual((result["remindOn"], result["consumeBy"]), ("2026-09-27", "2026-09-28"))
        for code in ("4104420034327", "4104420033641"):
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot | {"barcode": code}, temperature_c=4))
        # The separate coconut cooking cream retains its four-day instruction.
        cream = self.profile("Plant-based cream")
        package = lot | {"brand": "Alnatura", "barcode": "4104420240940"}
        self.assertEqual(self.lifecycle.opening_window(cream, package, temperature_c=4)["consumeBy"], "2026-09-29")
        self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, package, temperature_c=4))

    def test_cultivated_mushrooms_have_german_availability_without_an_opening_clock(self):
        for name in ("Fresh oyster mushrooms", "Oyster mushrooms, coarsely chopped", "King oyster mushroom", "Fresh shiitake slices", "Shiitake mushrooms, washed"):
            with self.subTest(name=name):
                profile = self.profile(name)
                region = profile["seasonality"]["regions"][0]
                self.assertEqual(region["sourceRegion"], "DE")
                self.assertEqual(region["basis"], "regional_seasonal_availability")
                for month in range(1, 13):
                    self.assertEqual(self.lifecycle.seasonal_availability(profile, country="DE", month=month)["status"], "year_round")
                self.assertEqual(self.lifecycle.seasonal_availability(profile, country="GR", month=9)["status"], "unknown")
                self.assertNotIn("rules", profile["afterOpening"])
        for name in ("Wild oyster mushrooms", "Frozen oyster mushrooms", "Dried shiitake mushrooms", "Dried shiitake mushrooms, rehydrated in water and sliced", "Shiitake or other mushrooms", "Shiitake soaking liquid", "Oyster sauce", "Pickled mushrooms", "Mushrooms"):
            with self.subTest(excluded=name):
                self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")

    def test_pickle_caper_artichoke_and_sugo_windows_require_the_verified_package(self):
        cases = (
            ("Pickled cucumbers", "4104420257603", 5),
            ("Diced pickled cucumber", "4104420228795", 5),
            ("Gherkins, thinly sliced", "4104420257641", 5),
            ("Pickles, chopped and drained", "4104420228832", 5),
            ("Capers in vinegar", "42298601", 5),
            ("Marinated artichoke hearts, cut into thirds", "40045559", 2),
            ("Tomato sauce", "4104420129603", 5),
        )
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura"}
        for name, code, days in cases:
            with self.subTest(name=name, code=code):
                profile = self.profile(name)
                package = lot | {"barcode": code}
                for barcode in (code, code.zfill(14)):
                    result = self.lifecycle.opening_window(profile, package | {"barcode": barcode}, temperature_c=4)
                    self.assertEqual((result["daysMin"], result["daysMax"]), (days, days))
                    self.assertEqual(result["consumeBy"], "2026-09-30" if days == 5 else "2026-09-27")
                    self.assertFalse(result["safetyGuarantee"])
                capped = self.lifecycle.opening_window(profile, package | {"bestBefore": "2026-09-26"}, temperature_c=4)
                self.assertEqual((capped["remindOn"], capped["consumeBy"]), ("2026-09-26", "2026-09-26"))
                for changes, temp in (({"brand": "Other brand"}, 4), ({"brand": ""}, 4), ({"barcode": None}, 4), ({"barcode": code[:-1] + str((int(code[-1]) + 1) % 10)}, 4), ({"storage": "pantry"}, 4), ({"openedAt": None}, 4), ({}, None), ({}, 5)):
                    self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, package | changes, temperature_c=temp))
        # Both exact brand labels are valid for this Origin sauce. Existing
        # Klassik/Kräuter packages retain their shorter two-day instructions.
        sauce = self.profile("Tomato sauce")
        for code, brand, days in (("4104420129603", "Alnatura Origin", 5), ("4104420213593", "Alnatura", 2), ("4104420213517", "Alnatura", 2)):
            self.assertEqual(self.lifecycle.opening_window(sauce, lot | {"barcode": code, "brand": brand}, temperature_c=4)["daysMax"], days)

    def test_preserved_vegetable_packages_do_not_cross_food_or_form_boundaries(self):
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Alnatura"}
        groups = (
            ("Pickled cucumbers", {"4104420257603", "4104420228795", "4104420257641", "4104420228832"}),
            ("Sweet-and-sour pickles, chopped", {"4104420257603", "4104420257641"}),
            ("Chopped capers", {"42298601"}),
            ("Marinated artichokes", {"40045559"}),
        )
        codes = set().union(*(codes for _, codes in groups))
        for name, allowed in groups:
            for code in codes:
                with self.subTest(name=name, code=code):
                    profile = self.profile(name)
                    self.assertEqual(profile["seasonality"]["status"], "not_applicable")
                    self.assertEqual("consumeBy" in self.lifecycle.opening_window(profile, lot | {"barcode": code}, temperature_c=4), code in allowed)
        for name in ("Cucumber", "Pickle brine", "Gherkin vinegar", "Pickled onions", "Pickled vegetables (peppers, corn, carrots, mushrooms, peas...)", "Salt-packed capers", "Caper berries", "Artichoke hearts", "Canned artichoke bottoms", "Frozen artichoke"):
            for code in codes:
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), lot | {"barcode": code}, temperature_c=4))

    def test_pineapple_product_overrides_generic_canned_guidance_without_fallback(self):
        profile = self.profile("Canned pineapple (cut into quarters)")
        lot = {"openedAt": "2026-09-25", "storage": "fridge"}
        generic = self.lifecycle.opening_window(profile, lot, temperature_c=4)
        self.assertEqual((generic["daysMin"], generic["daysMax"]), (5, 7))
        package = lot | {"brand": "Alnatura", "barcode": "4104420033900"}
        result = self.lifecycle.opening_window(profile, package, temperature_c=4)
        self.assertEqual((result["remindOn"], result["consumeBy"]), ("2026-09-28", "2026-09-28"))
        for changes, temp in (({"brand": "Other brand"}, 4), ({"brand": ""}, 4), ({"barcode": None}, 4), ({"barcode": "4104420129603"}, 4), ({"storage": "pantry"}, 4), ({}, None), ({}, 5)):
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, package | changes, temperature_c=temp))
        for name in ("Pineapple", "Fresh pineapple, diced", "Pineapple juice", "Pineapple syrup (from the can)"):
            self.assertNotIn("consumeBy", self.lifecycle.opening_window(self.profile(name), package, temperature_c=4))
        self.assertEqual(self.profile("Canned pineapple juice")["profileId"], "canned_high_acid")
        capped = self.lifecycle.opening_window(profile, package | {"bestBefore": "2026-09-26"}, temperature_c=4)
        self.assertEqual(capped["consumeBy"], "2026-09-26")
        self.assertEqual(self.lifecycle.opening_window(profile, package | {"useWithinDays": 1})["consumeBy"], "2026-09-26")

    def test_skyr_qualitative_guidance_never_becomes_an_invented_number(self):
        lot = {"openedAt": "2026-09-25", "storage": "fridge", "brand": "Arla"}
        for name in ("Skyr", "Package of skyr (150 g)", "Berry skyr", "Vanilla skyr"):
            with self.subTest(name=name):
                profile = self.profile(name)
                self.assertEqual(profile["afterOpening"]["status"], "label_required")
                self.assertEqual(profile["afterOpening"]["sourceIds"], ["arla_skyr_opening"])
                self.assertNotIn("rules", profile["afterOpening"])
                self.assertNotIn("consumeBy", self.lifecycle.opening_window(profile, lot, temperature_c=4))
                self.assertEqual(self.lifecycle.opening_window(profile, lot | {"useWithinDays": 2})["consumeBy"], "2026-09-27")
        for name in ("Skyr drink", "Vegan skyr", "Quark", "Greek yoghurt"):
            self.assertNotEqual(self.profile(name).get("profileId"), "skyr_label_required")

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
        for name in ("Frozen strawberries", "Strawberry jam", "Tomatoes (fresh or canned)", "Milk chocolate", "Milk (cow's milk or plant-based milk)"):
            with self.subTest(name=name):
                self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")
        for classification, unconfirmed in (("ambiguous", False), ("food", True), ("equipment", False)):
            payload = {"ingredients": [{"canonicalName": "Asparagus", "classification": classification, "needsSemanticConfirmation": unconfirmed}]}
            self.lifecycle.enrich_catalog_ingredients(payload)
            self.assertNotIn("lifecycle", payload["ingredients"][0])
        self.assertEqual(self.profile("Canned chopped tomatoes")["seasonality"]["status"], "not_applicable")
        self.assertEqual(self.profile("Dried tomatoes")["seasonality"]["status"], "not_applicable")
        self.assertNotIn("rules", self.profile("Milk powder")["afterOpening"])

    def test_country_month_and_calendar_scope(self):
        profile = self.profile("Asparagus")
        for month in (4, 5, 6):
            self.assertEqual(self.lifecycle.seasonal_availability(profile, country="de", month=month)["status"], "in_season")
        self.assertEqual(self.lifecycle.seasonal_availability(profile, country="FR", month=4)["status"], "unknown")
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
        for name in ("Turnip greens", "Yellow turnip, cut into 2 cm pieces", "Snow peas, parboiled", "Frozen snow peas", "Walnut oil", "Roasted hazelnuts", "Hazelnut flour", "Hazelnut paste", "Artichoke hearts (fresh or frozen)", "Frozen artichoke", "Bitter melon, seeds and pith removed, cut 1 cm wide", "Dried kiwi"):
            with self.subTest(excluded=name):
                self.assertEqual(self.profile(name)["seasonality"]["status"], "unknown")
        self.assertEqual(self.profile("Marinated artichoke hearts")["seasonality"]["status"], "not_applicable")

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
                if name == "Ketchup":
                    self.assertEqual(profile["afterOpening"]["status"], "label_required")
                    self.assertEqual(profile["afterOpening"]["reason"], "no_reviewed_numeric_opening_interval")
                    self.assertNotIn("rules", profile["afterOpening"])
                lot = {"openedAt": "2026-09-24", "brand": "Alnatura", "barcode": code, "storage": "fridge"}
                window = self.lifecycle.opening_window(profile, lot, temperature_c=4)
                self.assertEqual(window["status"], "label_required")
                self.assertNotIn("consumeBy", window)
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
