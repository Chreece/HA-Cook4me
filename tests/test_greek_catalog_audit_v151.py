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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v151_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV151Tests(unittest.TestCase):
    def test_v151_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v151.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v167",panel)
        self.assertIn("cook4me-panel-v167.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.32",panel)
        self.assertIn("?v=2026.9.21.32",panel)
        self.assertIn('"version": "2026.9.21.32"',manifest)
        self.assertIn("cook4me-panel-v150.js?v=2026.9.21.15",ui)

    def test_mint_and_spearmint_are_consistent(self):
        labels=load_presentation().labels()["el"]
        self.assertEqual(labels["mint"],"Μέντα")
        self.assertEqual(labels["spearmint"],"Δυόσμος")
        for key in ("dried mint","fresh mint","fresh mint leaf","mint and parsley","parsley and mint","mint leaf"):
            self.assertIn("μέντ",labels[key].casefold())
            self.assertNotIn("δυόσμ",labels[key].casefold())

    def test_bay_leaf_and_chervil_are_natural_greek(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["bay leaf"],"Φύλλο δάφνης")
        self.assertEqual(labels["dried bay leaf"],"Αποξηραμένο φύλλο δάφνης")
        self.assertEqual(labels["thyme and bay leaf"],"Θυμάρι και φύλλο δάφνης")
        self.assertEqual(labels["chervil"],"Φραγκομαϊντανός (chervil)")

    def test_seaweed_and_roe_keep_recognizable_market_names(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "nori sheet":"Φύλλο νόρι",
            "kombu seaweed sheet":"Φύλλο κόμπου",
            "salmon roe":"Αυγά σολομού (ikura)",
            "tarako cod roe":"Tarako (αυγά μπακαλιάρου)",
            "kelp":"Kelp (φύκια)",
            "hijiki seaweed":"Hijiki (φύκια χιτζίκι)",
            "aonori":"Aonori (πράσινα φύκια)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_sweetener_and_specialty_vegetable_terms(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "monk fruit sweetener":"Γλυκαντικό monk fruit (λουό χαν γκουό)",
            "pomegranate molasses":"Μελάσα ροδιού (πετιμέζι ροδιού)",
            "small kohlrabi with leaf":"Μικρό κολράμπι με φύλλα",
            "burdock root":"Ρίζα κολλιτσίδας (gobo)",
            "lotus root":"Ρίζα λωτού (renkon)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_brine_miso_and_matcha_terms(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["sauerkraut juice"],"Άλμη ξινολάχανου")
        self.assertEqual(labels["sauerkraut with juice"],"Ξινολάχανο με την άλμη του")
        self.assertEqual(labels["red miso"],"Κόκκινο μίσο (aka miso)")
        self.assertEqual(labels["matcha green tea"],"Μάτσα (πράσινο τσάι σε σκόνη)")
        self.assertEqual(labels["ground matcha tea"],"Μάτσα σε σκόνη")

    def test_search_aliases_cover_sixth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("μέντα",aliases["mint"])
        self.assertIn("φραγκομαϊντανός",aliases["chervil"])
        self.assertIn("ikura",aliases["salmon roe"])
        self.assertIn("tarako",aliases["tarako cod roe"])
        self.assertIn("μελάσα ροδιού",aliases["pomegranate molasses"])
        self.assertIn("gobo",aliases["burdock root"])
        self.assertIn("renkon",aliases["lotus root"])
        self.assertIn("άλμη ξινολάχανου",aliases["sauerkraut juice"])

    def test_curated_scope_expanded_sixth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),295)
        self.assertGreaterEqual(len(data["searchAliases"]),130)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
