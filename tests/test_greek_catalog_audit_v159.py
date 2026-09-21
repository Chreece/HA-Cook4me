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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v159_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV159Tests(unittest.TestCase):
    def test_v159_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v159.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v162",panel)
        self.assertIn("cook4me-panel-v162.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.27",panel)
        self.assertIn("?v=2026.9.21.27",panel)
        self.assertIn('"version": "2026.9.21.27"',manifest)
        self.assertIn("cook4me-panel-v158.js?v=2026.9.21.23",ui)

    def test_bunch_and_handful_quantities_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "handful of spinach":"Μια χούφτα σπανάκι",
            "handful of blueberry":"Μια χούφτα μύρτιλα",
            "bunch of parsley":"Ματσάκι μαϊντανό",
            "bunch of fresh coriander":"Ματσάκι φρέσκο κόλιανδρο",
            "bunch of watercress":"Ματσάκι νεροκάρδαμο",
            "small bunch of wild fennel":"Μικρό ματσάκι άγριο μάραθο",
            "sprig of fresh lemon verbena":"Κλωναράκι φρέσκιας λουίζας",
            "cubed butter":"Βούτυρο σε κύβους",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_singular_mushroom_sources_are_singular_in_greek(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "button mushroom":"Λευκό μανιτάρι champignon",
            "chanterelle mushroom":"Μανιτάρι κανθαρέλα",
            "chestnut mushroom":"Καφέ μανιτάρι champignon",
            "enoki mushroom":"Μανιτάρι enoki",
            "king oyster mushroom":"Μανιτάρι eryngii (king oyster)",
            "maitake mushroom":"Μανιτάρι maitake",
            "nameko mushroom":"Μανιτάρι nameko",
            "oyster mushroom":"Μανιτάρι πλευρώτους",
            "porcini mushroom":"Μανιτάρι porcini",
            "shiitake mushroom":"Μανιτάρι shiitake",
            "shimeji mushroom":"Μανιτάρι shimeji",
            "wood ear mushroom":"Μανιτάρι wood ear (αυτί του Ιούδα)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_mushroom_preparation_state_is_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["dried shiitake mushroom"],"Αποξηραμένο μανιτάρι shiitake")
        self.assertEqual(labels["fresh shiitake mushroom"],"Φρέσκο μανιτάρι shiitake")
        self.assertEqual(labels["fresh oyster mushroom"],"Φρέσκο μανιτάρι πλευρώτους")
        self.assertEqual(labels["small dried shiitake mushroom"],"Μικρό αποξηραμένο μανιτάρι shiitake")

    def test_search_aliases_cover_fourteenth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("χούφτα σπανάκι",aliases["handful of spinach"])
        self.assertIn("ματσάκι μαϊντανό",aliases["bunch of parsley"])
        self.assertIn("champignon",aliases["button mushroom"])
        self.assertIn("eryngii",aliases["king oyster mushroom"])
        self.assertIn("πορτσίνι",aliases["porcini mushroom"])
        self.assertIn("wood ear",aliases["wood ear mushroom"])

    def test_curated_scope_expanded_fourteenth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),621)
        self.assertGreaterEqual(len(data["searchAliases"]),289)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
