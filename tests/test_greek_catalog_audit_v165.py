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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v165_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV165Tests(unittest.TestCase):
    def test_v165_is_inherited_by_active_v171(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v165.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v171",panel)
        self.assertIn("cook4me-panel-v171.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.36",panel)
        self.assertIn("?v=2026.9.21.36",panel)
        self.assertIn('"version": "2026.9.21.36"',manifest)
        self.assertIn("cook4me-panel-v164.js?v=2026.9.21.29",ui)

    def test_singular_nut_forms_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "almond":"Αμύγδαλο",
            "blanched almond":"Λευκό αμύγδαλο",
            "roasted almond":"Καβουρδισμένο αμύγδαλο",
            "toasted almond":"Καβουρδισμένο αμύγδαλο",
            "whole almond":"Ολόκληρο αμύγδαλο",
            "cashew":"Κάσιους",
            "roasted cashew":"Καβουρδισμένο κάσιους",
            "unsalted cashew":"Ανάλατο κάσιους",
            "peanut":"Αράπικο φιστίκι",
            "chestnut":"Κάστανο",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_singular_dried_and_frozen_produce_is_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "plum":"Δαμάσκηνο",
            "dried plum":"Αποξηραμένο δαμάσκηνο",
            "frozen plum":"Κατεψυγμένο δαμάσκηνο",
            "cherry tomato":"Ντοματίνι",
            "dried tomato":"Αποξηραμένη ντομάτα",
            "dried carrot":"Αποξηραμένο καρότο",
            "boiled okra":"Βρασμένη μπάμια",
            "dried okra":"Αποξηραμένη μπάμια",
            "frozen okra":"Κατεψυγμένη μπάμια",
            "dried anchovy":"Αποξηραμένη αντζούγια",
            "dried shrimp":"Αποξηραμένη γαρίδα",
            "salted shrimp":"Αλατισμένη γαρίδα",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_singular_seed_forms_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "caraway seed":"Σπόρος αγριοκύμινου",
            "coriander seed":"Σπόρος κόλιανδρου",
            "cumin seed":"Σπόρος κύμινου",
            "hemp seed":"Σπόρος κάνναβης",
            "mustard seed":"Σπόρος μουστάρδας",
            "pomegranate seed":"Σπόρος ροδιού",
            "pumpkin seed":"Κολοκυθόσπορος",
            "sunflower seed":"Ηλιόσπορος",
            "white mustard seed":"Σπόρος λευκής μουστάρδας",
            "whole cumin seed":"Ολόκληρος σπόρος κύμινου",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_plural_market_search_remains_available(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("αμύγδαλα",aliases["almond"])
        self.assertIn("καβουρδισμένα αμύγδαλα",aliases["roasted almond"])
        self.assertIn("κάστανα",aliases["chestnut"])
        self.assertIn("δαμάσκηνα",aliases["plum"])
        self.assertIn("ντοματίνια",aliases["cherry tomato"])
        self.assertIn("αποξηραμένες ντομάτες",aliases["dried tomato"])
        self.assertIn("κατεψυγμένες μπάμιες",aliases["frozen okra"])
        self.assertIn("σπόροι κύμινου",aliases["cumin seed"])
        self.assertIn("ηλιόσποροι",aliases["sunflower seed"])

    def test_curated_scope_crosses_one_thousand(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1031)
        self.assertGreaterEqual(len(data["searchAliases"]),454)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
