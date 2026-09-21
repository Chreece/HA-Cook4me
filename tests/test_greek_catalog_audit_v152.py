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
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v152_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogAuditV152Tests(unittest.TestCase):
    def test_v152_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v152.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v173",panel)
        self.assertIn("cook4me-panel-v173.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.38",panel)
        self.assertIn("?v=2026.9.21.38",panel)
        self.assertIn('"version": "2026.9.21.38"',manifest)
        self.assertIn("cook4me-panel-v151.js?v=2026.9.21.16",ui)

    def test_far_ro_and_jujube_family_are_not_literal_mislabels(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["quick-cook farro"],"Farro γρήγορου μαγειρέματος")
        self.assertEqual(labels["red dates"],"Κόκκινα τζίτζιφα (jujube / Chinese dates)")
        self.assertEqual(labels["dried red dates"],"Αποξηραμένα κόκκινα τζίτζιφα (jujube)")
        self.assertEqual(labels["jujube"],"Τζίτζιφα (jujube)")
        self.assertEqual(labels["“bird tongue” pasta"],"Κριθαράκι (bird’s tongue pasta)")

    def test_asian_condiments_keep_package_names(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "mentsuyu":"Mentsuyu (συμπυκνωμένη βάση για νουντλς)",
            "light soy sauce":"Light soy sauce (ανοιχτόχρωμη σάλτσα σόγιας)",
            "dark soy sauce":"Dark soy sauce (σκούρα σάλτσα σόγιας)",
            "sweet soy sauce":"Sweet soy sauce (γλυκιά σάλτσα σόγιας)",
            "nuoc mam fish sauce":"Nước mắm (βιετναμέζικη σάλτσα ψαριού)",
            "ponzu":"Ponzu (ιαπωνική σάλτσα εσπεριδοειδών)",
            "shiro dashi":"Shiro dashi (λευκή βάση dashi)",
            "doubanjiang":"Doubanjiang (πικάντικη ζυμωμένη πάστα φασολιών)",
            "shaoxing wine":"Shaoxing (κινέζικο κρασί ρυζιού)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_gelatin_sheet_singulars_are_correct(self):
        labels=load_presentation().labels()["el"]
        self.assertEqual(labels["gelatin sheet"],"Φύλλο ζελατίνης")
        self.assertEqual(labels["gelatine leaf"],"Φύλλο ζελατίνης")
        self.assertEqual(labels["leaf gelatine"],"Φύλλο ζελατίνης")
        self.assertEqual(labels["gelatin sheet soaked in cold water"],"Μουλιασμένο φύλλο ζελατίνης")
        self.assertEqual(labels["pre-soaked gelatin sheet"],"Προμουλιασμένο φύλλο ζελατίνης")
        self.assertEqual(labels["gelatin sheets"],"Φύλλα ζελατίνης")

    def test_kasha_fish_sauce_and_slurry_terms(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(labels["roasted buckwheat for kasha"],"Κάσα (καβουρδισμένο φαγόπυρο)")
        self.assertEqual(labels["anchovy fish sauce"],"Σάλτσα ψαριού από αντζούγια")
        self.assertEqual(labels["red yeast rice sauce"],"Σάλτσα από κόκκινο ζυμωμένο ρύζι (red yeast rice)")
        self.assertEqual(labels["starch slurry"],"Μείγμα αμύλου με υγρό (starch slurry)")

    def test_search_aliases_cover_seventh_pass_terms(self):
        aliases=load_presentation().locale_search_aliases()["el"]
        self.assertIn("φάρρο",aliases["quick-cook farro"])
        self.assertIn("jujube",aliases["red dates"])
        self.assertIn("κριθαράκι",aliases["“bird tongue” pasta"])
        self.assertIn("tsuyu",aliases["mentsuyu"])
        self.assertIn("nước mắm",aliases["nuoc mam fish sauce"])
        self.assertIn("kasha",aliases["roasted buckwheat for kasha"])
        self.assertIn("φύλλο ζελατίνης",aliases["gelatin sheet"])

    def test_curated_scope_expanded_seventh_time(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),329)
        self.assertGreaterEqual(len(data["searchAliases"]),156)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
