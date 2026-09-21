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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v162_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV162Tests(unittest.TestCase):
    def test_v162_is_inherited_by_active_v164(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v162.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v164",panel)
        self.assertIn("cook4me-panel-v164.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.29",panel)
        self.assertIn("?v=2026.9.21.29",panel)
        self.assertIn('"version": "2026.9.21.29"',manifest)
        self.assertIn("cook4me-panel-v161.js?v=2026.9.21.26",ui)

    def test_temperature_and_preparation_are_not_flattened(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "boiling water":"Νερό που βράζει",
            "hot water":"Ζεστό νερό",
            "lukewarm water":"Χλιαρό νερό",
            "cold milk":"Κρύο γάλα",
            "hot milk":"Ζεστό γάλα",
            "melted butter":"Λιωμένο βούτυρο",
            "melted chocolate":"Λιωμένη σοκολάτα",
            "melted cooking chocolate":"Λιωμένη κουβερτούρα",
            "gelatin sheets soaked in cold water":"Φύλλα ζελατίνης μουλιασμένα σε κρύο νερό",
            "warm cooked rice":"Ζεστό μαγειρεμένο ρύζι",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_recipe_form_and_measure_words_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "block chocolate":"Πλάκα σοκολάτας",
            "chocolate bars":"Πλάκες σοκολάτας",
            "knob of butter":"Ένα κομματάκι βούτυρο",
            "half a lemon":"Μισό λεμόνι",
            "one-third vanilla pod":"⅓ λοβού βανίλιας",
            "broccoli floret":"Μπουκετάκι μπρόκολου",
            "small broccoli floret":"Μικρό μπουκετάκι μπρόκολου",
            "cauliflower floret":"Μπουκετάκι κουνουπιδιού",
            "medium egg, 50–55 g":"Μεσαίο αυγό, 50–55 g",
            "tortillas, 20 cm diameter":"Τορτίγιες διαμέτρου 20 εκ.",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_recipe_purpose_qualifiers_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "butter for greasing the moulds":"Βούτυρο για βουτύρωμα των φορμών",
            "flour for coating":"Αλεύρι για αλεύρωμα",
            "powdered sugar for decorating":"Ζάχαρη άχνη για διακόσμηση",
            "sugar for caramel":"Ζάχαρη για καραμέλα",
            "sugar for syrup":"Ζάχαρη για σιρόπι",
            "milk for marinating":"Γάλα για μαρινάρισμα",
            "madeleines to serve":"Μαντλέν για το σερβίρισμα",
            "toasted almond flakes for decorating":"Καβουρδισμένα αμύγδαλα φιλέ για διακόσμηση",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_singular_and_cut_forms_remain_visible(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "baby spinach leaf":"Φύλλο τρυφερού σπανακιού",
            "burger patty":"Μπιφτέκι για μπέργκερ",
            "crouton":"Κρουτόν",
            "julienned carrot":"Καρότο κομμένο ζουλιέν",
            "zucchini flower":"Κολοκυθοανθός",
            "pumpkin, 8 mm thick":"Κολοκύθα πάχους 8 mm",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_search_aliases_cover_seventeenth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("νερό που βράζει",aliases["boiling water"])
        self.assertIn("χλιαρό νερό",aliases["lukewarm water"])
        self.assertIn("λιωμένο βούτυρο",aliases["melted butter"])
        self.assertIn("πλάκα σοκολάτας",aliases["block chocolate"])
        self.assertIn("μπουκετάκι μπρόκολου",aliases["broccoli floret"])
        self.assertIn("καρότο σε λεπτές λωρίδες",aliases["julienned carrot"])
        self.assertIn("μπιφτέκι",aliases["burger patty"])

    def test_curated_scope_expanded_seventeenth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),879)
        self.assertGreaterEqual(len(data["searchAliases"]),362)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
