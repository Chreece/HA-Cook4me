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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v157_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV157Tests(unittest.TestCase):
    def test_v157_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v157.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.8",panel)
        self.assertIn("?v=2026.9.22.8",panel)
        self.assertIn('"version": "2026.9.22.8"',manifest)
        self.assertIn("cook4me-panel-v156.js?v=2026.9.21.21",ui)

    def test_meat_and_bread_forms_keep_cut_information(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "bacon strips":"Λωρίδες μπέικον",
            "beef in 30 g cubes":"Μοσχάρι σε κύβους των 30 g",
            "centre-cut pork loin":"Κεντρικό κομμάτι χοιρινού καρέ",
            "pork belly, 2–3 cm thick":"Χοιρινή πανσέτα πάχους 2–3 εκ.",
            "slices of sandwich bread":"Φέτες ψωμιού τοστ",
            "slices of white bread":"Φέτες λευκού ψωμιού",
            "slices of wholewheat bread":"Φέτες ψωμιού ολικής άλεσης",
            "thin slices of cooked ham":"Λεπτές φέτες βραστού ζαμπόν",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_seafood_singular_plural_and_portions_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "headless prawn":"Γαρίδα χωρίς κεφάλι",
            "headless shrimp":"Γαρίδα χωρίς κεφάλι",
            "large prawn tails":"Ουρές μεγάλων γαρίδων",
            "shrimp tails":"Ουρές γαρίδων",
            "marinated anchovy":"Μαριναρισμένη αντζούγια",
            "dried baby sardine":"Αποξηραμένη μικρή σαρδέλα",
            "salmon fillets, 125 g each":"Φιλέτα σολομού, 125 g το καθένα",
            "salt cod fillets, 150 g each":"Φιλέτα παστού μπακαλιάρου, 150 g το καθένα",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_false_friend_fish_names_keep_safe_market_or_species_name(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["hairtail fish"],"Τριχιούρος (hairtail / cutlassfish, Trichiurus)")
        self.assertNotEqual(labels["hairtail fish"],"Σπαθόψαρο")
        self.assertEqual(labels["ling fish"],"Λινγκ (Molva molva)")
        self.assertEqual(labels["milkfish belly"],"Κοιλιά μίλκφις / μπάνγκους (milkfish / bangus)")

    def test_dried_and_piece_forms_are_not_collapsed(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "dried daikon strips":"Αποξηραμένες λωρίδες ντάικον (daikon)",
            "fried taro chunks":"Κομμάτια τηγανητού τάρο",
            "pieces of crustless white bread":"Κομμάτια λευκού ψωμιού χωρίς κόρα",
            "sun-dried tomato":"Λιαστή ντομάτα",
            "venison fillet, 180 g portions":"Μερίδες φιλέτου ελαφιού των 180 g",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_search_aliases_cover_twelfth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("beef cubes",aliases["beef in 30 g cubes"])
        self.assertIn("headless shrimp",aliases["headless shrimp"])
        self.assertIn("hairtail",aliases["hairtail fish"])
        self.assertIn("cutlassfish",aliases["hairtail fish"])
        self.assertIn("bangus",aliases["milkfish belly"])
        self.assertIn("molva molva",aliases["ling fish"])
        self.assertIn("λιαστή ντομάτα",aliases["sun-dried tomato"])

    def test_curated_scope_expanded_twelfth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),556)
        self.assertGreaterEqual(len(data["searchAliases"]),254)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
