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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v173_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV173Tests(unittest.TestCase):
    def test_v173_is_inherited_by_active_v177(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v173.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.7",panel)
        self.assertIn("?v=2026.9.22.7",panel)
        self.assertIn('"version": "2026.9.22.7"',manifest)
        self.assertIn("cook4me-panel-v172.js?v=2026.9.21.37",ui)

    def test_olive_singulars_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["olive"],"Ελιά")
        self.assertEqual(labels["greek olive"],"Ελληνική ελιά")
        self.assertEqual(labels["taggiasca olive"],"Ελιά Τατζάσκα")

    def test_sauce_and_protein_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("μαρμελάδα",aliases["jam"])
        self.assertIn("πέστο",aliases["pesto"])
        self.assertIn("σάλτσα πόνζου",aliases["ponzu sauce"])
        self.assertIn("μοσχαρίσια μπριζόλα",aliases["beef steak"])
        self.assertIn("γλώσσα μοσχαριού",aliases["beef tongue"])
        self.assertIn("κομμάτια κοτόπουλου",aliases["chicken pieces"])
        self.assertIn("αρνίσιο κότσι",aliases["lamb shank"])

    def test_herb_drink_and_specialty_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("ρίγανη",aliases["oregano"])
        self.assertIn("σαφράν σε σκόνη",aliases["saffron powder"])
        self.assertIn("καπνιστή πάπρικα",aliases["smoked paprika"])
        self.assertIn("τσάι",aliases["tea"])
        self.assertIn("λευκό κρασί",aliases["white wine"])
        self.assertIn("φύλλο ζελατίνης",aliases["gelatine leaf"])
        self.assertIn("μανιτάρι σιτάκε",aliases["shiitake mushroom"])
        self.assertIn("λάδι τρούφας",aliases["truffle oil"])

    def test_massive_500_group_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1262)
        self.assertGreaterEqual(len(data["searchAliases"]),2612)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
