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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v161_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV161Tests(unittest.TestCase):
    def test_v161_is_inherited_by_active_v166(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v161.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v166",panel)
        self.assertIn("cook4me-panel-v166.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.31",panel)
        self.assertIn("?v=2026.9.21.31",panel)
        self.assertIn('"version": "2026.9.21.31"',manifest)
        self.assertIn("cook4me-panel-v160.js?v=2026.9.21.25",ui)

    def test_parser_fragments_are_honest_greek_fragments(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "cups of":"Φλιτζάνια από…",
            "grams of":"Γραμμάρια από…",
            "half a":"Μισό…",
            "handful of":"Μια χούφτα από…",
            "pinch of":"Μια πρέζα από…",
            "sprig of":"Κλωναράκι από…",
            "stalk of":"Κοτσάνι από…",
            "tablespoon of":"Μια κουταλιά της σούπας από…",
            "tbsp":"κ.σ.",
            "tsp":"κ.γ.",
            "whole":"Ολόκληρο…",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)
            self.assertNotIn("Απροσδιόριστο",labels.get(key,""))

    def test_singular_seafood_sources_are_singular_in_greek(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "clam":"Αχιβάδα",
            "mussel":"Μύδι",
            "oyster":"Στρείδι",
            "prawn":"Γαρίδα",
            "shrimp":"Γαρίδα",
            "scallop":"Χτένι",
            "king prawn":"Μεγάλη γαρίδα",
            "raw prawn":"Ωμή γαρίδα",
            "cooked mussel":"Μαγειρεμένο μύδι",
            "frozen cooked shrimp":"Κατεψυγμένη μαγειρεμένη γαρίδα",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_singular_herb_leaves_are_singular(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "basil leaf":"Φύλλο βασιλικού",
            "coriander leaf":"Φύλλο κόλιανδρου",
            "mint leaf":"Φύλλο μέντας",
            "sage leaf":"Φύλλο φασκόμηλου",
            "thyme leaf":"Φύλλο θυμαριού",
            "fresh basil leaf":"Φρέσκο φύλλο βασιλικού",
            "fresh mint leaf":"Φρέσκο φύλλο μέντας",
            "fresh thyme leaf":"Φρέσκο φύλλο θυμαριού",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_explicit_recipe_measures_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "cup of parsley":"1 φλιτζάνι μαϊντανό",
            "cup of fresh coriander":"1 φλιτζάνι φρέσκο κόλιανδρο",
            "pinch of salt":"Μια πρέζα αλάτι",
            "tablespoon of olive oil":"1 κ.σ. ελαιόλαδο",
            "tbsp coriander":"1 κ.σ. κόλιανδρο",
            "tbsp fresh mint":"1 κ.σ. φρέσκια μέντα",
            "tsp turmeric":"1 κ.γ. κουρκουμά",
            "tsp toasted sesame seed":"1 κ.γ. καβουρδισμένο σουσάμι",
            "teaspoon of vanilla extract":"1 κ.γ. εκχύλισμα βανίλιας",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_search_aliases_cover_sixteenth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("αχιβάδα",aliases["clam"])
        self.assertIn("στρείδι",aliases["oyster"])
        self.assertIn("φύλλο μέντας",aliases["mint leaf"])
        self.assertIn("φλιτζάνι μαϊντανό",aliases["cup of parsley"])
        self.assertIn("κ.σ. ελαιόλαδο",aliases["tablespoon of olive oil"])
        self.assertIn("κ.γ. καβουρδισμένο σουσάμι",aliases["tsp toasted sesame seed"])

    def test_curated_scope_expanded_sixteenth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),788)
        self.assertGreaterEqual(len(data["searchAliases"]),330)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
