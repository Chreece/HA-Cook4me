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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v156_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV156Tests(unittest.TestCase):
    def test_v156_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v156.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v167",panel)
        self.assertIn("cook4me-panel-v167.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.32",panel)
        self.assertIn("?v=2026.9.21.32",panel)
        self.assertIn('"version": "2026.9.21.32"',manifest)
        self.assertIn("cook4me-panel-v155.js?v=2026.9.21.20",ui)

    def test_slices_keep_physical_form(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "bacon slice":"Φέτα μπέικον",
            "bacon slices":"Φέτες μπέικον",
            "bread slice":"Φέτα ψωμιού",
            "bread slices":"Φέτες ψωμιού",
            "emmental cheese slices":"Φέτες Έμενταλ",
            "mozzarella slices":"Φέτες μοτσαρέλας",
            "pancetta slices":"Φέτες παντσέτας",
            "pork belly slices":"Φέτες χοιρινής πανσέτας",
            "thin slices of ginger":"Λεπτές φέτες τζίντζερ",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_shavings_crumbles_and_pieces_keep_form(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "gouda cheese shreds":"Τριμμένο γκούντα",
            "parmesan shavings":"Φλοίδες παρμεζάνας",
            "crumbled feta cheese":"Θρυμματισμένη φέτα",
            "crumbled goat cheese":"Θρυμματισμένο κατσικίσιο τυρί",
            "bacon pieces":"Κομμάτια μπέικον",
            "chicken pieces":"Κομμάτια κοτόπουλου",
            "pieces of emmental cheese":"Κομμάτια Έμενταλ",
            "seitan in large pieces":"Σεϊτάν σε μεγάλα κομμάτια",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_sheet_singular_plural_is_preserved(self):
        labels=load_presentation().labels()["el"]
        self.assertEqual(labels["filo pastry sheets"],"Φύλλα κρούστας")
        self.assertEqual(labels["lasagna sheet"],"Φύλλο λαζάνιας")
        self.assertEqual(labels["lasagne sheet"],"Φύλλο λαζάνιας")
        self.assertEqual(labels["dry lasagna sheets"],"Ξερά φύλλα λαζάνιας")
        self.assertEqual(labels["gelatin sheet"],"Φύλλο ζελατίνης")
        self.assertEqual(labels["gelatin sheets"],"Φύλλα ζελατίνης")

    def test_asian_sauces_and_red_bean_pastes_keep_market_names(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "tianmianjiang sweet bean sauce":"Tianmianjiang (γλυκιά πάστα φασολιών)",
            "yakiniku sauce":"Yakiniku sauce (ιαπωνική σάλτσα για ψητό κρέας)",
            "yakitori sauce":"Yakitori tare (ιαπωνική σάλτσα yakitori)",
            "teriyaki marinade sauce":"Σάλτσα / μαρινάδα teriyaki",
            "sweet red bean paste":"Anko (γλυκιά πάστα κόκκινων φασολιών)",
            "smooth red bean paste":"Koshi-an (λεία πάστα κόκκινων φασολιών)",
            "chunky red bean paste":"Tsubu-an (πάστα κόκκινων φασολιών με κομμάτια)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_search_aliases_cover_eleventh_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("φέτες έμενταλ",aliases["emmental cheese slices"])
        self.assertIn("φλοίδες παρμεζάνας",aliases["parmesan shavings"])
        self.assertIn("phyllo sheets",aliases["filo pastry sheets"])
        self.assertIn("tianmianjiang",aliases["tianmianjiang sweet bean sauce"])
        self.assertIn("yakitori tare",aliases["yakitori sauce"])
        self.assertIn("anko",aliases["sweet red bean paste"])
        self.assertIn("koshi-an",aliases["smooth red bean paste"])
        self.assertIn("tsubu-an",aliases["chunky red bean paste"])

    def test_curated_scope_expanded_eleventh_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),514)
        self.assertGreaterEqual(len(data["searchAliases"]),236)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
