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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v167_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV167Tests(unittest.TestCase):
    def test_v167_is_active_and_versioned(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v167.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v167",panel)
        self.assertIn("cook4me-panel-v167.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.32",panel)
        self.assertIn("?v=2026.9.21.32",panel)
        self.assertIn('"version": "2026.9.21.32"',manifest)
        self.assertIn("cook4me-panel-v166.js?v=2026.9.21.31",ui)

    def test_bakery_singulars_and_details_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "biscuit":"Μπισκότο",
            "amaretti biscuit":"Μπισκότο αμαρέτι",
            "chocolate biscuit":"Μπισκότο σοκολάτας",
            "digestive biscuit":"Μπισκότο νταϊτζέστιβ",
            "ladyfinger biscuit":"Μπισκότο σαβαγιάρ",
            "shortbread biscuit":"Μπισκότο σόρτμπρεντ",
            "bread crumb":"Ψίχουλο ψωμιού",
            "white bread crumb":"Ψίχουλο λευκού ψωμιού",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_meat_cut_and_organ_singulars_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "beef cheek":"Μάγουλο μοσχαριού",
            "beef meatball":"Μοσχαρίσιο κεφτεδάκι",
            "beef rib":"Μοσχαρίσιο παϊδάκι",
            "chicken carcass":"Σκελετός κοτόπουλου",
            "chicken drumstick":"Κοπανάκι κοτόπουλου",
            "chicken liver":"Συκώτι κοτόπουλου",
            "lamb chop":"Αρνίσιο παϊδάκι",
            "meatball":"Κεφτεδάκι",
            "pork cheek":"Χοιρινό μάγουλο",
            "pork meatball":"Χοιρινό κεφτεδάκι",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_recipe_context_and_measure_fragments_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "tied beef":"Δεμένο κομμάτι μοσχαριού",
            "foie gras marinated in milk and patted dry":"Φουά γκρα μαριναρισμένο σε γάλα και σκουπισμένο στεγνά",
            "scoop of protein powder":"Μία μεζούρα πρωτεΐνης σε σκόνη",
            "splash of orange liqueur":"Μια μικρή δόση λικέρ πορτοκαλιού",
            "vial of orange blossom essence":"Φιαλίδιο εσάνς ανθών πορτοκαλιάς",
            "cinnamon stick":"Ξυλάκι κανέλας",
            "bamboo shoot":"Βλαστός μπαμπού",
            "textured soy protein soaked for 30 minutes":"Πρωτεΐνη σόγιας με υφή, μουλιασμένη για 30 λεπτά",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_choice_wording_is_not_dropped(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "favorite fruit":"Φρούτο της επιλογής σας",
            "favourite nuts":"Ξηροί καρποί της επιλογής σας",
            "favourite sausage":"Λουκάνικο της επιλογής σας",
            "herbs of choice":"Μυρωδικά της επιλογής σας",
            "lettuce of choice":"Μαρούλι της επιλογής σας",
            "preferred dressing":"Ντρέσινγκ της επιλογής σας",
            "vegetable puree of choice":"Πουρές λαχανικών της επιλογής σας",
            "vegetables of choice":"Λαχανικά της επιλογής σας",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_native_greek_fruit_and_preserve_wording(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "blackcurrant":"Μαύρο φραγκοστάφυλο",
            "cherry":"Κεράσι",
            "hazelnut":"Φουντούκι",
            "pecan nut":"Καρύδι πεκάν",
            "raisin":"Σταφίδα",
            "walnut":"Καρύδι",
            "cherry jam":"Μαρμελάδα κερασιού",
            "orange jam":"Μαρμελάδα πορτοκαλιού",
            "strawberry jam":"Μαρμελάδα φράουλας",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_search_aliases_cover_large_batch(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("μπισκότο",aliases["biscuit"])
        self.assertIn("μάγουλο μοσχαριού",aliases["beef cheek"])
        self.assertIn("κεφτεδάκι",aliases["meatball"])
        self.assertIn("φουντούκια",aliases["hazelnut"])
        self.assertIn("καρύδια",aliases["walnut"])
        self.assertIn("βλαστοί μπαμπού",aliases["bamboo shoot"])
        self.assertIn("ξυλάκια κανέλας",aliases["cinnamon stick"])

    def test_large_batch_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),1235)
        self.assertGreaterEqual(len(data["searchAliases"]),563)
        self.assertIn("twenty-second audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
