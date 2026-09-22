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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v170_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV170Tests(unittest.TestCase):
    def test_v170_is_inherited_by_active_v177(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v170.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v179",panel)
        self.assertIn("cook4me-panel-v179.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.6",panel)
        self.assertIn("?v=2026.9.22.6",panel)
        self.assertIn('"version": "2026.9.22.6"',manifest)
        self.assertIn("cook4me-panel-v169.js?v=2026.9.21.34",ui)

    def test_form_and_measure_details_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "banana slices":"Φέτες μπανάνας",
            "bunch of baby spinach":"Ματσάκι τρυφερού σπανακιού",
            "bunches of baby spinach":"Ματσάκια τρυφερού σπανακιού",
            "celery stalk":"Κοτσάνι σέλινου",
            "dried mango slices":"Φέτες αποξηραμένου μάνγκο",
            "bread slice":"Φέτα ψωμιού",
            "crumbled bread slices":"Θρυμματισμένες φέτες ψωμιού",
            "crumbled brioche":"Θρυμματισμένο μπριός",
            "cup of long-grain white rice":"1 φλιτζάνι λευκό μακρύκοκκο ρύζι",
            "cup of ground almond":"1 φλιτζάνι αλεσμένο αμύγδαλο",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_chocolate_and_baking_context_is_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "chocolate disc":"Δίσκος σοκολάτας",
            "chocolate ring":"Δαχτυλίδι σοκολάτας",
            "chocolate pieces":"Κομμάτια σοκολάτας",
            "cold water for soaking the gelatin":"Κρύο νερό για το μούλιασμα της ζελατίνης",
            "brown sugar for decorating":"Καστανή ζάχαρη για διακόσμηση",
            "cardamom, 1 cinnamon stick, 2 bay leaf":"Κάρδαμο, 1 ξυλάκι κανέλας και 2 φύλλα δάφνης",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_produce_grain_and_pantry_search_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("φέτες μπανάνας",aliases["banana slices"])
        self.assertIn("αγκινάρα",aliases["artichoke"])
        self.assertIn("κοτσάνι σέλινου",aliases["celery stalk"])
        self.assertIn("αλεύρι για όλες τις χρήσεις",aliases["all-purpose flour"])
        self.assertIn("καστανό μπασμάτι",aliases["brown basmati rice"])
        self.assertIn("νερό ζυμαρικών",aliases["cooked pasta water"])
        self.assertIn("μέλι ακακίας",aliases["acacia honey"])
        self.assertIn("λάδι αβοκάντο",aliases["avocado oil"])
        self.assertIn("σταγόνες σοκολάτας",aliases["chocolate chips"])

    def test_legume_seed_and_international_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("ενταμάμε",aliases["edamame bean"])
        self.assertIn("μαύρο σουσάμι",aliases["black sesame"])
        self.assertIn("σφιχτό τόφου",aliases["firm tofu"])
        self.assertIn("κίμτσι",aliases["kimchi"])
        self.assertIn("φύκια κόμπου",aliases["kombu"])
        self.assertIn("γκαράμ μασάλα",aliases["garam masala"])
        self.assertIn("φύλλα γκιόζα",aliases["gyoza wrappers"])
        self.assertIn("σάλτσα σατάι",aliases["satay sauce"])

    def test_massive_batch_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1255)
        self.assertGreaterEqual(len(data["searchAliases"]),1300)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
