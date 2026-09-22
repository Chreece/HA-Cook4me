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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v169_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV169Tests(unittest.TestCase):
    def test_v169_is_inherited_by_active_v177(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v169.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v178",panel)
        self.assertIn("cook4me-panel-v178.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.5",panel)
        self.assertIn("?v=2026.9.22.5",panel)
        self.assertIn('"version": "2026.9.22.5"',manifest)
        self.assertIn("cook4me-panel-v168.js?v=2026.9.21.33",ui)

    def test_beef_and_pork_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("μοσχάρι",aliases["beef"])
        self.assertIn("στήθος μοσχαριού",aliases["beef brisket"])
        self.assertIn("μάγουλα μοσχαριού",aliases["beef cheeks"])
        self.assertIn("φιλέτο μοσχαριού",aliases["beef fillet"])
        self.assertIn("κότσι μοσχαριού",aliases["beef shank"])
        self.assertIn("μπέικον",aliases["bacon"])
        self.assertIn("φέτα μπέικον",aliases["bacon slice"])
        self.assertIn("χοιρινή πανσέτα",aliases["fresh pork belly"])
        self.assertIn("ζαμπόν",aliases["ham"])

    def test_poultry_and_seafood_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("κοτόπουλο",aliases["chicken"])
        self.assertIn("φιλέτο κοτόπουλου",aliases["chicken fillet"])
        self.assertIn("ζωμός κοτόπουλου που βράζει",aliases["boiling chicken stock"])
        self.assertIn("καβούρι",aliases["crab"])
        self.assertIn("ψίχα καβουριού",aliases["crab meat"])
        self.assertIn("φρέσκος σολομός",aliases["fresh salmon"])
        self.assertIn("κατεψυγμένα θαλασσινά",aliases["frozen seafood"])
        self.assertIn("ιπτάμενο καλαμάρι",aliases["flying squid"])

    def test_dairy_and_sauce_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("αμυγδαλοβούτυρο",aliases["almond butter"])
        self.assertIn("παλαιωμένο γκούντα",aliases["aged gouda"])
        self.assertIn("μπρι",aliases["brie"])
        self.assertIn("καμαμπέρ",aliases["camembert"])
        self.assertIn("τσένταρ",aliases["cheddar"])
        self.assertIn("τυρί",aliases["cheese"])
        self.assertIn("σιρόπι αγαύης",aliases["agave syrup"])
        self.assertIn("σάλτσα μπάρμπεκιου",aliases["barbecue sauce"])
        self.assertIn("μπεσαμέλ",aliases["bechamel sauce"])
        self.assertIn("πάστα τσίλι",aliases["chili paste"])
        self.assertIn("μηλόξιδο",aliases["cider vinegar"])

    def test_one_thousand_alias_milestone(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1253)
        self.assertGreaterEqual(len(data["searchAliases"]),1000)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
