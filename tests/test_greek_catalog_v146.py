from pathlib import Path
import importlib.util
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
LOCALE=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


def load_presentation():
    path=ROOT/"custom_components"/"cook4me"/"catalog_presentation.py"
    spec=importlib.util.spec_from_file_location("cook4me_catalog_presentation_v146_test",path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class GreekCatalogV146Tests(unittest.TestCase):
    def test_v146_is_inherited_by_active_v161(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v146.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v163",panel)
        self.assertIn("cook4me-panel-v163.js",panel)
        self.assertIn("/cook4me_static/2026.9.21.28",panel)
        self.assertIn("?v=2026.9.21.28",panel)
        self.assertIn('"version": "2026.9.21.28"',manifest)
        self.assertIn("cook4me-panel-v145.js?v=2026.9.21.10",ui)

    def test_curated_greek_overlay_fixes_literal_terms(self):
        data=json.loads(LOCALE.read_text(encoding="utf-8"))
        labels=data["labels"]
        expected={
            "veal":"Μοσχαράκι",
            "watercress":"Νεροκάρδαμο",
            "waxy potato":"Πατάτες σφιχτής σάρκας",
            "white pudding":"Λευκό λουκάνικο τύπου white pudding",
            "cornflour":"Κορν φλάουρ (άμυλο καλαμποκιού)",
            "venison tenderloin":"Φιλέτο ελαφιού",
            "pork loin":"Χοιρινό καρέ",
            "mint":"Μέντα",
            "spearmint":"Δυόσμος",
            "kohlrabi":"Κολράμπι (γογγυλοκράμβη)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value)

    def test_overlay_has_meaningful_review_scope(self):
        data=json.loads(LOCALE.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(data["labels"]),60)
        self.assertGreaterEqual(len(data["searchAliases"]),15)
        self.assertEqual(data["language"],"el")
        self.assertIn("Curated native-Greek",data["translationSource"])

    def test_curated_labels_override_base_greek_locale(self):
        presentation=load_presentation()
        labels=presentation.labels()["el"]
        self.assertEqual(labels["veal"],"Μοσχαράκι")
        self.assertEqual(labels["watercress"],"Νεροκάρδαμο")
        self.assertEqual(labels["mint"],"Μέντα")
        self.assertEqual(labels["spearmint"],"Δυόσμος")

    def test_greek_supermarket_synonyms_are_searchable(self):
        presentation=load_presentation()
        aliases=presentation.locale_search_aliases()["el"]
        self.assertIn("άμυλο καλαμποκιού",aliases["cornflour"])
        self.assertIn("κορν φλάουρ",aliases["cornstarch"])
        self.assertIn("πατάτες για βράσιμο",aliases["waxy potato"])
        self.assertIn("βαλεριάνα",aliases["lamb's lettuce"])

    def test_search_index_accepts_locale_synonym_overlay(self):
        text=(ROOT/"custom_components"/"cook4me"/"catalog_search_index.py").read_text(encoding="utf-8")
        core=(ROOT/"custom_components"/"cook4me"/"release_catalog_v60_core.py").read_text(encoding="utf-8")
        self.assertIn("localized_search_aliases=None",text)
        self.assertIn("for language, rows in (localized_search_aliases or {}).items()",text)
        self.assertIn("_presentation.locale_search_aliases()",core)


if __name__=="__main__":
    unittest.main()
