from pathlib import Path
import importlib.util
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


def load_presentation():
    path=ROOT/"custom_components"/"cook4me"/"catalog_presentation.py"
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v150_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV150Tests(unittest.TestCase):
    def test_v150_is_inherited_by_active_v154(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v150.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v154",panel)
        self.assertIn("cook4me-panel-v154.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.19",panel)
        self.assertIn("?v=2026.9.21.19",panel)
        self.assertIn('"version": "2026.9.21.19"',manifest)
        self.assertIn("cook4me-panel-v149.js?v=2026.9.21.14",ui)

    def test_fifth_pass_fixes_deli_and_preserved_food_terms(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "milk jam":"Dulce de leche (καραμελωμένο γάλα)",
            "preserved lemon":"Λεμόνι διατηρημένο σε αλάτι (preserved lemon)",
            "bacon lardon":"Κυβάκια μπέικον (lardons)",
            "smoked bacon lardon":"Καπνιστά κυβάκια μπέικον (lardons)",
            "cooked salami":"Μαγειρεμένο σαλάμι (cooked salami)",
            "cured ham":"Ζαμπόν ωρίμανσης",
            "guanciale":"Γκουαντσιάλε",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_fifth_pass_improves_dairy_oils_and_sauces(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "mold-ripened cheese":"Τυρί ωρίμανσης με ευγενή μούχλα",
            "melting cheese":"Τυρί για λιώσιμο",
            "fromage frais":"Fromage frais (φρέσκο τυρί)",
            "ricotta salata":"Ricotta salata (αλατισμένη ρικότα)",
            "canola oil":"Κραμβέλαιο (canola)",
            "peanut oil":"Λάδι αράπικου φιστικιού (αραχιδέλαιο)",
            "worcestershire sauce":"Σάλτσα Worcestershire (Γούστερ)",
            "sriracha sauce":"Sriracha (καυτερή σάλτσα τσίλι)",
            "harissa":"Harissa (πάστα καυτερής πιπεριάς)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_spelt_family_uses_greek_market_name(self):
        labels=load_presentation().labels()["el"]
        self.assertEqual(labels["spelt"],"Σπέλτα (ντίνκελ)")
        self.assertEqual(labels["spelt flour"],"Αλεύρι σπέλτα (ντίνκελ)")
        self.assertEqual(labels["wholemeal spelt flour"],"Αλεύρι σπέλτα ολικής άλεσης")
        self.assertEqual(labels["pearl barley"],"Κριθάρι περλέ")

    def test_search_aliases_cover_fifth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("dulce de leche",aliases["milk jam"])
        self.assertIn("λαρδόν",aliases["bacon lardon"])
        self.assertIn("γκουαντσιάλε",aliases["guanciale"])
        self.assertIn("τυρί για λιώσιμο",aliases["melting cheese"])
        self.assertIn("αραχιδέλαιο",aliases["peanut oil"])
        self.assertIn("σάλτσα γούστερ",aliases["worcestershire sauce"])
        self.assertIn("σπέλτα",aliases["spelt"])

    def test_curated_scope_expanded_fifth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),255)
        self.assertGreaterEqual(len(data["searchAliases"]),110)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
