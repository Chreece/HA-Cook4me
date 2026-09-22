from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV181Tests(unittest.TestCase):
    def test_backend_only_audit_keeps_current_frontend_build(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v178",panel)
        self.assertIn("cook4me-panel-v178.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.5",panel)
        self.assertIn('"version": "2026.9.22.5"',manifest)

    def test_thirty_sixth_pass_preserves_recipe_and_market_context(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertEqual(
            labels["cornflour mixed into a little stock"],
            "Κορν φλάουρ ανακατεμένο με λίγο ζωμό",
        )
        self.assertEqual(
            labels["store-bought yakiniku sauce"],
            "Έτοιμη σάλτσα yakiniku",
        )

    def test_revised_display_labels_are_searchable(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        for key in (
            "cornflour mixed into a little stock",
            "store-bought yakiniku sauce",
        ):
            aliases={str(value).strip().casefold() for value in data["searchAliases"][key]}
            self.assertIn(key.casefold(),aliases,key)
            self.assertIn(data["labels"][key].casefold(),aliases,key)

    def test_thirty_sixth_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1277)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8790)
        self.assertIn("thirty-sixth audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
