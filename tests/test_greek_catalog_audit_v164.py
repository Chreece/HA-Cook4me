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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v164_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV164Tests(unittest.TestCase):
    def test_v164_is_inherited_by_active_v172(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v164.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v172",panel)
        self.assertIn("cook4me-panel-v172.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.37",panel)
        self.assertIn("?v=2026.9.21.37",panel)
        self.assertIn('"version": "2026.9.21.37"',manifest)
        self.assertIn("cook4me-panel-v163.js?v=2026.9.21.28",ui)

    def test_singular_leaf_and_small_forms_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "cabbage leaf":"Φύλλο λάχανου",
            "celery leaf":"Φύλλο σέλινου",
            "lettuce leaf":"Φύλλο μαρουλιού",
            "parsley leaf":"Φύλλο μαϊντανού",
            "savoy cabbage leaf":"Φύλλο λάχανου σαβόι",
            "baby cuttlefish":"Μικρή σουπιά",
            "baby octopus":"Μικρό χταπόδι",
            "baby potato":"Μικρή πατάτα",
            "mini pepper":"Μίνι πιπεριά",
            "mini sausage":"Μίνι λουκάνικο",
            "small chicken wing":"Μικρή φτερούγα κοτόπουλου",
            "small cooked potato":"Μικρή μαγειρεμένη πατάτα",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_cut_and_product_form_are_not_flattened(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "julienned onion":"Κρεμμύδι κομμένο ζουλιέν",
            "julienned potato":"Πατάτα κομμένη ζουλιέν",
            "canned corn kernels":"Κόκκοι καλαμποκιού κονσέρβας",
            "soup meat portion":"Μερίδα κρέατος για σούπα",
            "hollowed piquillo pepper":"Αδειασμένη πιπεριά πικίγιο",
            "pearl onion":"Κρεμμυδάκι πέρλα",
            "small lamb rib":"Μικρό αρνίσιο παϊδάκι",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_size_and_grain_semantics_are_kept(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "medium-grain couscous":"Κουσκούς μέτριου κόκκου",
            "medium-grain couscous semolina":"Σιμιγδάλι κουσκούς μέτριου κόκκου",
            "new potato":"Πατάτα νέας σοδειάς",
            "organic new potato":"Βιολογική πατάτα νέας σοδειάς",
            "red potato":"Κόκκινη πατάτα",
            "white potato":"Λευκή πατάτα",
            "large fresh raw shrimp":"Μεγάλη φρέσκια ωμή γαρίδα",
            "large frozen raw shrimp":"Μεγάλη κατεψυγμένη ωμή γαρίδα",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_recipe_role_and_market_wording_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "baby spinach salad":"Τρυφερό σπανάκι για σαλάτα",
            "fresh or canned grape leaf":"Φρέσκο αμπελόφυλλο ή αμπελόφυλλο κονσέρβας",
            "fresh or frozen baby onion":"Φρέσκο ή κατεψυγμένο μικρό κρεμμύδι",
            "potato for mash":"Πατάτα για πουρέ",
            "padron pepper":"Πιπεριά Παδρόν",
            "piquillo pepper":"Πιπεριά πικίγιο",
            "shishito pepper":"Πιπεριά σισίτο",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_search_aliases_cover_nineteenth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("φύλλο λάχανου",aliases["cabbage leaf"])
        self.assertIn("κρεμμύδι ζουλιέν",aliases["julienned onion"])
        self.assertIn("μίνι πιπεριά",aliases["mini pepper"])
        self.assertIn("κόκκοι καλαμποκιού κονσέρβας",aliases["canned corn kernels"])
        self.assertIn("μερίδα κρέατος για σούπα",aliases["soup meat portion"])
        self.assertIn("κουσκούς μέτριου κόκκου",aliases["medium-grain couscous"])
        self.assertIn("πατάτα για πουρέ",aliases["potato for mash"])

    def test_curated_scope_expanded_nineteenth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),974)
        self.assertGreaterEqual(len(data["searchAliases"]),423)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
