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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v149_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV149Tests(unittest.TestCase):
    def test_v149_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v149.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v177",panel)
        self.assertIn("cook4me-panel-v177.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.4",panel)
        self.assertIn("?v=2026.9.22.4",panel)
        self.assertIn('"version": "2026.9.22.4"',manifest)
        self.assertIn("cook4me-panel-v148.js?v=2026.9.21.13",ui)

    def test_generic_pistachio_does_not_claim_aegina_origin(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        for key in (
            "pistachio","pistachio cream","pistachio paste","pistachio kernels",
            "ground pistachio","roasted pistachio","shelled pistachio",
        ):
            self.assertIn(key,labels)
            self.assertNotIn("Αιγίνης",labels[key])
        self.assertEqual(labels["pistachio"],"Κελυφωτά φιστίκια (pistachios)")

    def test_fourth_pass_improves_specialty_market_terms(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "sesame puree":"Ταχίνι (πάστα σουσαμιού)",
            "sesame salt":"Γκομάσιο (αλάτι με σουσάμι)",
            "wood ear mushroom":"Μανιτάρι wood ear (αυτί του Ιούδα)",
            "king oyster mushroom":"Μανιτάρι eryngii (king oyster)",
            "glass noodle":"Glass noodles (διάφανα νουντλς)",
            "jasmine rice":"Ρύζι jasmine (γιασεμί)",
            "glutinous rice":"Sticky rice (κολλώδες ρύζι)",
            "passion fruit":"Passion fruit (πασιφλόρα)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_nut_and_seed_wording_is_natural(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["pine nuts"],"Κουκουνάρια")
        self.assertEqual(labels["toasted pine nuts"],"Καβουρδισμένα κουκουνάρια")
        self.assertEqual(labels["chia seed"],"Σπόροι chia (τσία)")
        self.assertEqual(labels["almond puree"],"Πάστα αμυγδάλου")
        self.assertEqual(labels["hazelnut puree"],"Πάστα φουντουκιού")

    def test_search_aliases_include_greek_and_package_names(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("φιστίκι αιγίνης",aliases["pistachio"])
        self.assertIn("eryngii",aliases["king oyster mushroom"])
        self.assertIn("cellophane noodles",aliases["glass noodle"])
        self.assertIn("sticky rice",aliases["glutinous rice"])
        self.assertIn("πασιφλόρα",aliases["passion fruit"])
        self.assertIn("γκομάσιο",aliases["sesame salt"])

    def test_curated_scope_expanded_fourth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),220)
        self.assertGreaterEqual(len(data["searchAliases"]),85)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
