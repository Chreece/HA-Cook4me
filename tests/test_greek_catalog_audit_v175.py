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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v175_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV175Tests(unittest.TestCase):
    def test_v175_is_inherited_by_active_v177(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v175.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v178",panel)
        self.assertIn("cook4me-panel-v178.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.5",panel)
        self.assertIn("?v=2026.9.22.5",panel)
        self.assertIn('"version": "2026.9.22.5"',manifest)
        self.assertIn("cook4me-panel-v174.js?v=2026.9.22.1",ui)

    def test_every_legitimate_base_ingredient_has_curated_aliases(self):
        base=json.loads(BASE.read_text(encoding="utf-8"))["labels"]
        aliases=json.loads(CURATED.read_text(encoding="utf-8"))["searchAliases"]
        missing=set(base)-set(aliases)
        self.assertEqual(missing,INTENTIONAL_PARSER_FRAGMENTS)

    def test_parser_fragments_are_not_promoted_to_supermarket_search(self):
        aliases=json.loads(CURATED.read_text(encoding="utf-8"))["searchAliases"]
        for key in INTENTIONAL_PARSER_FRAGMENTS:
            self.assertNotIn(key,aliases)

    def test_remaining_everyday_aliases_are_natural(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("κεχρί",aliases["millet"])
        self.assertIn("διατροφική μαγιά",aliases["nutritional yeast flakes"])
        self.assertIn("νουτέλα",aliases["nutella"])
        self.assertIn("παστινάκι",aliases["parsnip"])
        self.assertIn("κουκουνάρι",aliases["pine nut"])
        self.assertIn("ρόδι",aliases["pomegranate"])
        self.assertIn("λαβράκι",aliases["sea bass"])
        self.assertIn("τσιπούρα",aliases["sea bream"])
        self.assertIn("σουμάκ",aliases["sumac"])
        self.assertIn("γλυκοπατάτα",aliases["sweet potato"])
        self.assertIn("γιούζου",aliases["yuzu"])

    def test_vodka_shots_keep_measure_form(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertEqual(data["labels"]["shots of mild-tasting vodka"],"Σφηνάκια βότκας ήπιας γεύσης")
        self.assertIn("σφηνάκια βότκας",data["searchAliases"]["shots of mild-tasting vodka"])

    def test_completion_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1264)
        self.assertGreaterEqual(len(data["searchAliases"]),3689)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
