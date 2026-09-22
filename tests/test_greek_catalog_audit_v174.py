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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v174_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV174Tests(unittest.TestCase):
    def test_v174_is_inherited_by_active_v176(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v174.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v176",panel)
        self.assertIn("cook4me-panel-v176.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.3",panel)
        self.assertIn("?v=2026.9.22.3",panel)
        self.assertIn('"version": "2026.9.22.3"',manifest)
        self.assertIn("cook4me-panel-v173.js?v=2026.9.21.38",ui)

    def test_quail_egg_singular_is_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["quail egg"],"Αυγό ορτυκιού")

    def test_everyday_aliases_are_searchable(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("τυρί κότατζ",aliases["chilled cottage cheese"])
        self.assertIn("τσιαπάτα",aliases["ciabatta"])
        self.assertIn("κράνμπερι",aliases["cranberry"])
        self.assertIn("κρουασάν",aliases["croissants"])
        self.assertIn("κρουτόν",aliases["crouton"])
        self.assertIn("φετουτσίνι",aliases["fettuccine"])
        self.assertIn("γκι",aliases["ghee"])
        self.assertIn("εσπρέσο",aliases["espresso"])

    def test_pantry_and_protein_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("κιτρικό οξύ",aliases["citric acid"])
        self.assertIn("ντάσι",aliases["dashi"])
        self.assertIn("ανθός αλατιού",aliases["fleur de sel"])
        self.assertIn("μπριζόλα σπάλας",aliases["chuck steak"])
        self.assertIn("αχιβάδες",aliases["clams"])
        self.assertIn("μελάνι σουπιάς",aliases["cuttlefish ink"])
        self.assertIn("φουά γκρα",aliases["foie gras"])

    def test_quail_egg_aliases_remain_natural(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("αυγό ορτυκιού",aliases["quail egg"])
        self.assertIn("αυγά ορτυκιού",aliases["quail egg"])

    def test_massive_600_group_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1263)
        self.assertGreaterEqual(len(data["searchAliases"]),3213)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
