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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v155_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV155Tests(unittest.TestCase):
    def test_v155_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v155.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v171",panel)
        self.assertIn("cook4me-panel-v171.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.36",panel)
        self.assertIn("?v=2026.9.21.36",panel)
        self.assertIn('"version": "2026.9.21.36"',manifest)
        self.assertIn("cook4me-panel-v154.js?v=2026.9.21.19",ui)

    def test_singular_food_labels_are_not_pluralized(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["anchovy"],"Αντζούγια")
        self.assertEqual(labels["sardine"],"Σαρδέλα")
        self.assertEqual(labels["bread roll"],"Ψωμάκι")
        self.assertEqual(labels["burger bun"],"Ψωμάκι για μπέργκερ")

    def test_bakery_and_dairy_market_names_are_clear(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "flatbread":"Flatbread (πλατύ ψωμί)",
            "brick pastry sheets":"Φύλλα μπρικ (brick pastry)",
            "baguette slices":"Φέτες μπαγκέτας",
            "cottage cheese":"Cottage cheese (τυρί κότατζ)",
            "buttermilk":"Buttermilk (βουτυρόγαλα)",
            "skyr":"Skyr (σκιρ)",
            "processed cheese portion":"Μερίδα επεξεργασμένου τυριού",
            "processed cheese portions":"Μερίδες επεξεργασμένου τυριού",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_produce_and_fish_labels_avoid_misleading_literal_terms(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "bok choy":"Pak choi / bok choy (πακ τσόι)",
            "daikon radish":"Daikon (λευκό ραπανάκι)",
            "skate wing":"Φτερούγα σαλαχιού",
            "headless crucian carp":"Κουτσουράς χωρίς κεφάλι",
            "whole albacore tuna":"Ολόκληρος τόνος albacore (λευκός τόνος)",
            "spanish mackerel":"Spanish mackerel (είδος σκουμπριού)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)
        self.assertNotEqual(labels["headless crucian carp"],"Πεταλούδα χωρίς κεφάλι")

    def test_fermented_condiments_keep_recognizable_product_names(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "gochujang":"Gochujang (κορεάτικη πάστα τσίλι)",
            "doenjang":"Doenjang (κορεάτικη πάστα σόγιας)",
            "cheonggukjang fermented soybean paste":"Cheonggukjang (κορεάτικη πάστα ζυμωμένης σόγιας)",
            "ajvar":"Ajvar (βαλκανική πάστα ψητής πιπεριάς)",
            "sambal":"Sambal (ινδονησιακό καυτερό καρύκευμα)",
            "fish sauce":"Σάλτσα ψαριού (fish sauce)",
            "miso paste":"Miso paste (πάστα μίσο)",
            "salt-pickled cherry blossoms":"Άνθη κερασιάς σε αλάτι (sakura)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_search_aliases_cover_tenth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("κουτσουράς",aliases["headless crucian carp"])
        self.assertIn("pak choi",aliases["bok choy"])
        self.assertIn("daikon",aliases["daikon radish"])
        self.assertIn("gochujang",aliases["gochujang"])
        self.assertIn("cheonggukjang",aliases["cheonggukjang fermented soybean paste"])
        self.assertIn("sakura",aliases["salt-pickled cherry blossoms"])
        self.assertIn("cottage cheese",aliases["cottage cheese"])

    def test_curated_scope_expanded_tenth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),429)
        self.assertGreaterEqual(len(data["searchAliases"]),218)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
