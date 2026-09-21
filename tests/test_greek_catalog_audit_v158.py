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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v158_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV158Tests(unittest.TestCase):
    def test_v158_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v158.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v164",panel)
        self.assertIn("cook4me-panel-v164.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.29",panel)
        self.assertIn("?v=2026.9.21.29",panel)
        self.assertIn('"version": "2026.9.21.29"',manifest)
        self.assertIn("cook4me-panel-v157.js?v=2026.9.21.22",ui)

    def test_cloves_sprigs_stalks_and_heads_keep_count_form(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "garlic clove":"Σκελίδα σκόρδου",
            "small garlic clove":"Μικρή σκελίδα σκόρδου",
            "fresh coriander sprig":"Κλωναράκι φρέσκου κόλιανδρου",
            "rosemary sprig":"Κλωναράκι δεντρολίβανου",
            "fresh thyme sprig":"Κλωναράκι φρέσκου θυμαριού",
            "parsley stalk":"Κοτσάνι μαϊντανού",
            "lemongrass stalk":"Βλαστός λεμονόχορτου",
            "green asparagus stalk":"Βλαστός πράσινου σπαραγγιού",
            "head of lettuce":"Κεφάλι μαρουλιού",
            "heads of lettuce":"Κεφάλια μαρουλιού",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_portion_and_piece_weights_are_not_lost(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "atsuage fried tofu, 130 g per piece":"Atsuage (τηγανητό τόφου), 130 g το τεμάχιο",
            "cod fillets, 150 g each":"Φιλέτα μπακαλιάρου, 150 g το καθένα",
            "french quenelles, 40–50 g each":"Γαλλικές κενέλ, 40–50 g η καθεμία",
            "goose breast, 400 g each":"Στήθος χήνας, περίπου 400 g ανά τεμάχιο",
            "quails, 160–170 g each":"Ορτύκια, 160–170 g το καθένα",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_package_and_portion_words_are_preserved(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "cheese portions":"Μερίδες τυριού",
            "mozzarella ball":"Μπάλα μοτσαρέλας",
            "spoonfuls of salted ricotta":"Κουταλιές αλατισμένης ρικότα",
            "package of smoked tofu":"Συσκευασία καπνιστού τόφου",
            "package of skyr":"Συσκευασία skyr",
            "packet of baking powder":"Φακελάκι μπέικιν πάουντερ",
            "packet taco seasoning mix":"Φακελάκι μείγματος καρυκευμάτων taco",
            "packages of vanilla pudding powder":"Συσκευασίες σκόνης πουτίγκας βανίλιας",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_search_aliases_cover_thirteenth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("σκελίδα σκόρδου",aliases["garlic clove"])
        self.assertIn("κλωναράκι δεντρολίβανου",aliases["rosemary sprig"])
        self.assertIn("κεφάλι μαρουλιού",aliases["head of lettuce"])
        self.assertIn("μπάλα μοτσαρέλας",aliases["mozzarella ball"])
        self.assertIn("cod fillets 150g",aliases["cod fillets, 150 g each"])
        self.assertIn("baking powder packet",aliases["packet of baking powder"])

    def test_curated_scope_expanded_thirteenth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),590)
        self.assertGreaterEqual(len(data["searchAliases"]),272)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
