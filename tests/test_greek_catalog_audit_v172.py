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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v172_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV172Tests(unittest.TestCase):
    def test_v172_is_inherited_by_active_v177(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v172.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v177",panel)
        self.assertIn("cook4me-panel-v177.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.4",panel)
        self.assertIn("?v=2026.9.22.4",panel)
        self.assertIn('"version": "2026.9.22.4"',manifest)
        self.assertIn("cook4me-panel-v171.js?v=2026.9.21.36",ui)

    def test_remaining_display_context_is_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["large leek stalk"],"Μεγάλο κοτσάνι πράσου")
        self.assertEqual(
            labels["christmas tea infused into 80 ml water"],
            "Χριστουγεννιάτικο τσάι εκχυλισμένο σε 80 ml νερού",
        )

    def test_seafood_and_bakery_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("κυπρίνος",aliases["carp"])
        self.assertIn("αστακός",aliases["lobster"])
        self.assertIn("πεσκανδρίτσα",aliases["monkfish"])
        self.assertIn("πλευρώτους",aliases["oyster mushroom"])
        self.assertIn("ωμή γαρίδα",aliases["raw shrimp"])
        self.assertIn("μπαγκέτα",aliases["baguette"])
        self.assertIn("κρουασάν",aliases["croissant"])
        self.assertIn("παντεσπάνι",aliases["sponge cake"])

    def test_drink_and_spice_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("μπίρα",aliases["beer"])
        self.assertIn("καφές",aliases["coffee"])
        self.assertIn("σαμπάνια",aliases["champagne"])
        self.assertIn("μάτσα",aliases["matcha tea"])
        self.assertIn("δάφνη",aliases["bay"])
        self.assertIn("γαρίφαλο",aliases["clove"])
        self.assertIn("αλεσμένο κακουλέ",aliases["ground cardamom"])

    def test_plant_protein_aliases(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("συσκευασία καπνιστού τόφου",aliases["package of smoked tofu"])
        self.assertIn("κοτολέτες σεϊτάν",aliases["seitan cutlets"])
        self.assertIn("σεϊτάν σε μεγάλα κομμάτια",aliases["seitan in large pieces"])
        self.assertIn("μεταξένιο τόφου",aliases["silken tofu"])
        self.assertIn("μαλακό τόφου",aliases["soft tofu"])

    def test_massive_alias_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1259)
        self.assertGreaterEqual(len(data["searchAliases"]),2112)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
