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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v148_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV148Tests(unittest.TestCase):
    def test_v148_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v148.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v171",panel)
        self.assertIn("cook4me-panel-v171.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.36",panel)
        self.assertIn("?v=2026.9.21.36",panel)
        self.assertIn('"version": "2026.9.21.36"',manifest)
        self.assertIn("cook4me-panel-v147.js?v=2026.9.21.12",ui)

    def test_third_pass_fixes_legume_produce_and_baking_terms(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "baked bean":"Φασόλια σε σάλτσα ντομάτας (baked beans)",
            "snow pea":"Μπιζέλια mangetout (snow peas)",
            "garden bean":"Κοινά φασόλια",
            "mature bean":"Ξερά φασόλια",
            "jerusalem artichoke":"Τοπιναμπούρ (αγκινάρα Ιερουσαλήμ)",
            "romanesco cabbage":"Κουνουπίδι ρομανέσκο",
            "firm potato":"Πατάτα σφιχτής σάρκας",
            "plain flour":"Αλεύρι για όλες τις χρήσεις",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_third_pass_preserves_recognizable_international_food_names(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "bonito flakes":"Κατσουομπούσι (νιφάδες παλαμίδας)",
            "sake lees":"Sake kasu (υπόλειμμα ζύμωσης σάκε)",
            "takuan pickled daikon":"Τακουάν (ντάικον τουρσί)",
            "doenjang soybean paste":"Ντοεντζάνγκ (κορεάτικη πάστα σόγιας)",
            "wonton dumplings":"Γουόντον",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_fish_and_shellfish_labels_are_more_recognizable(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "pollock":"Πόλακ (pollock)",
            "halibut":"Ιππόγλωσσος (halibut)",
            "yellow croaker":"Yellow croaker (κίτρινη σκιαινά)",
            "langoustines":"Καραβίδες (langoustines)",
            "crayfish":"Καραβίδες γλυκού νερού (crayfish)",
            "yellowtail":"Μαγιάτικο (yellowtail / hamachi)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_edamame_family_uses_market_name(self):
        labels=load_presentation().labels()["el"]
        for key in ("edamame","edamame bean","frozen edamame","frozen edamame bean"):
            self.assertIn("edamame",labels[key].casefold())

    def test_search_aliases_cover_third_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("τοπιναμπούρ",aliases["jerusalem artichoke"])
        self.assertIn("κατσουομπούσι",aliases["bonito flakes"])
        self.assertIn("hamachi",aliases["yellowtail"])
        self.assertIn("αλεύρι για όλες τις χρήσεις",aliases["plain flour"])
        self.assertIn("καραβίδες γλυκού νερού",aliases["crayfish"])

    def test_curated_scope_keeps_growing_without_touching_identity(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),180)
        self.assertGreaterEqual(len(data["searchAliases"]),60)
        self.assertIn("audit",data["translationSource"])
        presentation=(ROOT/"custom_components"/"cook4me"/"catalog_presentation.py").read_text(encoding="utf-8")
        self.assertIn("display_name",presentation)
        self.assertIn("locale_search_aliases",presentation)


if __name__=="__main__":
    unittest.main()
