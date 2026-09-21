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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v171_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV171Tests(unittest.TestCase):
    def test_v171_is_active_and_versioned(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v171.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v171",panel)
        self.assertIn("cook4me-panel-v171.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.36",panel)
        self.assertIn("?v=2026.9.21.36",panel)
        self.assertIn('"version": "2026.9.21.36"',manifest)
        self.assertIn("cook4me-panel-v170.js?v=2026.9.21.35",ui)

    def test_choice_and_singular_display_fixes(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["any berries"],"Μούρα της επιλογής σας")
        self.assertEqual(labels["any fruit"],"Φρούτα της επιλογής σας")
        self.assertEqual(labels["black olive"],"Μαύρη ελιά")

    def test_produce_and_grain_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("ρόκα",aliases["arugula"])
        self.assertIn("αβοκάντο",aliases["avocado"])
        self.assertIn("παντζάρι",aliases["beetroot"])
        self.assertIn("μαύρη τρούφα",aliases["black truffle"])
        self.assertIn("λαχανάκια βρυξελλών",aliases["brussels sprouts"])
        self.assertIn("σελινόριζα",aliases["celeriac"])
        self.assertIn("κανθαρέλες",aliases["chanterelles"])
        self.assertIn("κριθάρι",aliases["barley"])
        self.assertIn("μαύρο ρύζι",aliases["black rice"])
        self.assertIn("καστανό μπασμάτι",aliases["brown basmati rice"])

    def test_pantry_and_international_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("μπαχάρι",aliases["allspice"])
        self.assertIn("γλυκάνισος",aliases["anise"])
        self.assertIn("μαγειρική σόδα",aliases["bicarbonate of soda"])
        self.assertIn("μαύρο τσάι",aliases["black tea"])
        self.assertIn("κατζούν",aliases["cajun seasoning"])
        self.assertIn("κάρι",aliases["curry"])
        self.assertIn("γκαράμ μασάλα",aliases["garam masala"])
        self.assertIn("γουασάμπι",aliases["wasabi"])

    def test_choice_aliases_are_searchable(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("μούρα της επιλογής σας",aliases["any berries"])
        self.assertIn("φρούτα της επιλογής σας",aliases["any fruit"])
        self.assertIn("μαύρες ελιές",aliases["black olive"])

    def test_massive_alias_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1258)
        self.assertGreaterEqual(len(data["searchAliases"]),1703)
        self.assertIn("twenty-sixth audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
