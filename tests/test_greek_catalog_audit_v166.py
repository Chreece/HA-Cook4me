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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v166_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV166Tests(unittest.TestCase):
    def test_v166_is_inherited_by_active_v175(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v166.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v175",panel)
        self.assertIn("cook4me-panel-v175.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.2",panel)
        self.assertIn("?v=2026.9.22.2",panel)
        self.assertIn('"version": "2026.9.22.2"',manifest)
        self.assertIn("cook4me-panel-v165.js?v=2026.9.21.30",ui)

    def test_legume_singular_forms_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "adzuki bean":"Φασόλι αζούκι",
            "bean":"Φασόλι",
            "black bean":"Μαύρο φασόλι",
            "borlotti bean":"Φασόλι μπαρμπούνι",
            "broad bean":"Κουκί",
            "chickpea":"Ρεβίθι",
            "white bean":"Λευκό φασόλι",
            "green bean":"Πράσινο φασολάκι",
            "red lentil":"Κόκκινη φακή",
            "green lentil":"Πράσινη φακή",
            "lentil":"Φακή",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_legume_preparation_state_is_not_pluralized_away(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "canned chickpea":"Ρεβίθι κονσέρβας",
            "cooked chickpea":"Μαγειρεμένο ρεβίθι",
            "dried chickpea":"Ξερό ρεβίθι",
            "dried white bean":"Ξερό λευκό φασόλι",
            "frozen broad bean":"Κατεψυγμένο κουκί",
            "soaked white bean":"Μουλιασμένο λευκό φασόλι",
            "canned cooked lentil":"Βρασμένη φακή κονσέρβας",
            "dried green lentil":"Ξερή πράσινη φακή",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_mushroom_and_fruit_singular_forms_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "mushroom":"Μανιτάρι",
            "cultivated mushroom":"Μανιτάρι καλλιέργειας",
            "pickled mushroom":"Μανιτάρι τουρσί",
            "white mushroom":"Λευκό μανιτάρι",
            "blackberry":"Βατόμουρο",
            "blueberry":"Μύρτιλο",
            "date":"Χουρμάς",
            "fig":"Σύκο",
            "grape":"Σταφύλι",
            "raspberry":"Σμέουρο",
            "strawberry":"Φράουλα",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_form_and_package_details_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "grapefruit segments":"Τμήματα γκρέιπφρουτ",
            "stuffing zucchini":"Κολοκύθι για γέμισμα",
            "separated egg":"Αυγό χωρισμένο σε κρόκο και ασπράδι",
            "french onion soup mix in a sachet":"Φακελάκι μείγματος γαλλικής κρεμμυδόσουπας",
            "cans of poppy seed filling":"Κονσέρβες γέμισης παπαρουνόσπορου",
            "pink peppercorn":"Ροζ κόκκος πιπεριού",
            "green asparagus spears":"Βλαστοί πράσινων σπαραγγιών",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_plural_supermarket_aliases_remain_searchable(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("φασόλια",aliases["bean"])
        self.assertIn("ρεβίθια",aliases["chickpea"])
        self.assertIn("λευκά φασόλια",aliases["white bean"])
        self.assertIn("κόκκινες φακές",aliases["red lentil"])
        self.assertIn("μανιτάρια",aliases["mushroom"])
        self.assertIn("βατόμουρα",aliases["blackberry"])
        self.assertIn("μύρτιλα",aliases["blueberry"])
        self.assertIn("σύκα",aliases["fig"])
        self.assertIn("σταφύλια",aliases["grape"])
        self.assertIn("φράουλες",aliases["strawberry"])

    def test_large_batch_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1132)
        self.assertGreaterEqual(len(data["searchAliases"]),509)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
