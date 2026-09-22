from pathlib import Path
import importlib.util
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
BASE=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"el.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"

INTENTIONAL_PARSER_FRAGMENTS={
    "confit of","cups of","fleur de sel and","grams of","half a","handful of",
    "large","peeled","pinch of","portion of","red","salt and","sprig of",
    "tablespoon of","tails of","tbsp","teaspoon of dried","tender","thick",
    "tomato or","tsp","tsp fresh","washed","whole",
}


def load_presentation():
    path=ROOT/"custom_components"/"cook4me"/"catalog_presentation.py"
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v176_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV176Tests(unittest.TestCase):
    def test_v176_is_inherited_by_active_v177(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v177.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v177",panel)
        self.assertIn("cook4me-panel-v177.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.4",panel)
        self.assertIn("?v=2026.9.22.4",panel)
        self.assertIn('"version": "2026.9.22.4"',manifest)
        self.assertIn("cook4me-panel-v176.js?v=2026.9.22.3",ui)

    def test_quality_and_measure_details_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "good-quality olive oil":"Ελαιόλαδο καλής ποιότητας",
            "high-quality olive oil":"Ελαιόλαδο υψηλής ποιότητας",
            "good-quality rillettes":"Ριγιέτ καλής ποιότητας",
            "high-quality rillettes":"Ριγιέτ υψηλής ποιότητας",
            "julienned ginger":"Τζίντζερ κομμένο ζουλιέν",
            "french quenelles, 40–50 g":"Γαλλικές κενέλ, 40–50 g η καθεμία",
            "quail, 160–170 g":"Ορτύκι, 160–170 g",
            "quails, 160–170 g":"Ορτύκια, 160–170 g το καθένα",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_safe_synonym_clusters_share_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("colombo spice mix",aliases["colombo seasoning"])
        self.assertIn("colombo seasoning",aliases["colombo spice mix"])
        self.assertIn("powdered sugar",aliases["icing sugar"])
        self.assertIn("confectioners' sugar",aliases["powdered sugar"])
        self.assertIn("eggplant",aliases["aubergine"])
        self.assertIn("aubergine",aliases["eggplant"])
        self.assertIn("beef bouillon",aliases["beef stock"])
        self.assertIn("beef stock",aliases["beef bouillon"])
        self.assertIn("sponge finger",aliases["ladyfinger biscuit"])
        self.assertIn("ladyfinger",aliases["sponge finger biscuit"])

    def test_parser_fragments_stay_out_of_search(self):
        aliases=json.loads(CURATED.read_text(encoding="utf-8"))["searchAliases"]
        for key in INTENTIONAL_PARSER_FRAGMENTS:
            self.assertNotIn(key,aliases)

    def test_synonym_enrichment_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1272)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8299)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
