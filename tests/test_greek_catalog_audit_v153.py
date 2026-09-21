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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v153_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV153Tests(unittest.TestCase):
    def test_v153_is_inherited_by_active_v158(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v153.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v158",panel)
        self.assertIn("cook4me-panel-v158.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.23",panel)
        self.assertIn("?v=2026.9.21.23",panel)
        self.assertIn('"version": "2026.9.21.23"',manifest)
        self.assertIn("cook4me-panel-v152.js?v=2026.9.21.17",ui)

    def test_condensed_and_evaporated_milk_are_distinguished(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["condensed milk"],"Ζαχαρούχο γάλα (sweetened condensed milk)")
        self.assertEqual(labels["can of condensed milk"],"Κονσέρβα ζαχαρούχου γάλακτος")
        self.assertEqual(labels["unsweetened condensed milk"],"Γάλα εβαπορέ (χωρίς ζάχαρη)")
        self.assertEqual(labels["coffee cream"],"Κρέμα γάλακτος για καφέ")

    def test_stock_granules_are_natural_product_labels(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "chicken stock granules":"Κόκκοι ζωμού κοτόπουλου",
            "granulated chicken stock":"Κόκκοι ζωμού κοτόπουλου",
            "granulated chicken bouillon":"Κόκκοι ζωμού κοτόπουλου",
            "chinese-style stock granules":"Κόκκοι ζωμού κινέζικου τύπου",
            "french-style stock granules":"Κόκκοι ζωμού γαλλικού τύπου",
            "japanese dashi stock granules":"Κόκκοι ιαπωνικού dashi",
            "beef stock paste":"Συμπυκνωμένη πάστα ζωμού μοσχαριού",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_fermented_food_labels_use_natural_greek_and_market_names(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "fermented cucumber":"Ζυμωμένο αγγούρι",
            "fermented cucumber brine":"Άλμη από ζυμωμένα αγγούρια",
            "lightly fermented cucumber":"Ελαφρά ζυμωμένο αγγούρι",
            "salted fermented shrimp":"Saeujeot (αλατισμένες ζυμωμένες γαρίδες)",
            "sugar snap pea":"Sugar snap peas (τραγανά γλυκομπίζελα)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_tofu_specialties_keep_real_product_names(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "store-bought seasoned inari tofu pouches":"Έτοιμα καρυκευμένα inari-age (πουγκιά τηγανητού τόφου)",
            "thick tofu skin":"Yuba (παχιά πέτσα τόφου)",
            "atsuage fried tofu":"Atsuage (τηγανητό τόφου)",
            "firm atsuage fried tofu":"Σφιχτό atsuage (τηγανητό τόφου)",
            "large ganmodoki fried tofu":"Ganmodoki (τηγανητό τόφου με λαχανικά)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_legume_package_names_are_searchable(self):
        labels=load_presentation().labels()["el"]
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertEqual(labels["kidney bean"],"Φασόλια kidney")
        self.assertEqual(labels["cannellini bean"],"Φασόλια cannellini")
        self.assertEqual(labels["lima bean"],"Φασόλια Lima")
        self.assertEqual(labels["mung bean"],"Φασόλια mung")
        self.assertIn("φασόλια κίντνεϊ",aliases["kidney bean"])
        self.assertIn("κανελίνι",aliases["cannellini bean"])
        self.assertIn("φασόλια μουνγκ",aliases["mung bean"])

    def test_search_aliases_cover_eighth_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("ζαχαρούχο γάλα",aliases["condensed milk"])
        self.assertIn("εβαπορέ",aliases["unsweetened condensed milk"])
        self.assertIn("saeujeot",aliases["salted fermented shrimp"])
        self.assertIn("sugar snap peas",aliases["sugar snap pea"])
        self.assertIn("yuba",aliases["thick tofu skin"])
        self.assertIn("atsuage",aliases["atsuage fried tofu"])
        self.assertIn("ganmodoki",aliases["large ganmodoki fried tofu"])

    def test_curated_scope_expanded_eighth_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),363)
        self.assertGreaterEqual(len(data["searchAliases"]),178)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
