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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v147_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV147Tests(unittest.TestCase):
    def test_v147_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v147.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v169",panel)
        self.assertIn("cook4me-panel-v169.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.34",panel)
        self.assertIn("?v=2026.9.21.34",panel)
        self.assertIn('"version": "2026.9.21.34"',manifest)
        self.assertIn("cook4me-panel-v146.js?v=2026.9.21.11",ui)

    def test_second_pass_fixes_false_friends_and_supermarket_greek(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "cardamom":"Κακουλές (καρδάμωμο)",
            "mace":"Μασίς (άνθος μοσχοκάρυδου)",
            "saffron":"Σαφράν (κρόκος)",
            "red cabbage":"Μωβ λάχανο",
            "cavolo nero":"Cavolo nero (μαύρο λάχανο)",
            "corn on the cob":"Καλαμπόκι στο κοτσάνι",
            "pork spare rib":"Χοιρινά παϊδάκια (spare ribs)",
            "sole":"Γλώσσα (ψάρι)",
            "young chicken":"Κοτοπουλάκι",
            "boiled chicken gizzards":"Βρασμένα στομαχάκια κοτόπουλου",
            "rabbit thigh":"Μπούτι κουνελιού",
            "oxtail":"Μοσχαρίσια ουρά",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_cardamom_family_no_longer_uses_cress_wording(self):
        labels=load_presentation().labels()["el"]
        for key in ("cardamom","cardamom pod","cardamom pods","ground cardamom","shelled cardamom pods"):
            self.assertIn("κακουλ",labels[key].casefold())
            self.assertNotEqual(labels[key],"Κάρδαμο")

    def test_greek_search_aliases_cover_common_shop_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("κακουλές",aliases["cardamom"])
        self.assertIn("κρόκος",aliases["saffron"])
        self.assertIn("μωβ λάχανο",aliases["red cabbage"])
        self.assertIn("χοιρινά παϊδάκια",aliases["pork spare rib"])
        self.assertIn("γλώσσα",aliases["sole"])
        self.assertIn("μοσχαρίσια ουρά",aliases["oxtail"])

    def test_curated_scope_expanded_beyond_first_pass(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),130)
        self.assertGreaterEqual(len(data["searchAliases"]),30)
        self.assertIn("expanded",data["translationSource"])

    def test_old_awkward_phrases_are_not_final_display_labels(self):
        labels=load_presentation().labels()["el"]
        forbidden={
            "cardamom":"Κάρδαμο",
            "red cabbage":"Κόκκινο λάχανο",
            "sole":"Γλώσσα ψάρι",
            "young chicken":"Νεαρό κοτόπουλο",
            "pork spare rib":"Χοιρινές στηθοπλευρές",
            "corn on the cob":"Καλαμπόκι ολόκληρο",
        }
        for key,bad in forbidden.items():
            self.assertNotEqual(labels[key],bad)


if __name__=="__main__":
    unittest.main()
