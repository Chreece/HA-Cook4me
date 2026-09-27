from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV183Tests(unittest.TestCase):
    def test_backend_only_audit_keeps_current_frontend_build(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.7",panel)
        self.assertIn('"version": "2026.9.22.7"',manifest)

    def test_thirty_eighth_pass_puts_generic_market_terms_in_greek_first(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "glutinous rice":"Κολλώδες ρύζι (sticky rice)",
            "passion fruit":"Πασιφλόρα (passion fruit)",
            "yellow croaker":"Κίτρινη σκιαινά (yellow croaker)",
            "light soy sauce":"Ανοιχτόχρωμη σάλτσα σόγιας (light soy sauce)",
            "dark soy sauce":"Σκούρα σάλτσα σόγιας (dark soy sauce)",
            "sweet soy sauce":"Γλυκιά σάλτσα σόγιας (sweet soy sauce)",
            "light sweet soy sauce":"Ανοιχτόχρωμη γλυκιά σάλτσα σόγιας (light sweet soy sauce)",
            "soup soy sauce":"Σάλτσα σόγιας για σούπες (soup soy sauce)",
            "sugar snap pea":"Τραγανά γλυκομπίζελα (sugar snap peas)",
            "flatbread":"Πλατύ ψωμί (flatbread)",
            "buttermilk":"Βουτυρόγαλα (buttermilk)",
            "cottage cheese":"Τυρί κότατζ (cottage cheese)",
            "miso paste":"Πάστα μίσο",
            "bitter melon":"Πικρό πεπόνι / γκόγια (bitter melon)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)

    def test_revised_labels_keep_old_market_search_and_new_display_search(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        for key in (
            "glutinous rice","passion fruit","yellow croaker",
            "light soy sauce","dark soy sauce","sweet soy sauce",
            "light sweet soy sauce","soup soy sauce","sugar snap pea",
            "flatbread","buttermilk","cottage cheese","miso paste","bitter melon",
        ):
            aliases={str(value).strip().casefold() for value in data["searchAliases"][key]}
            self.assertIn(key.casefold(),aliases,key)
            self.assertIn(data["labels"][key].casefold(),aliases,key)

    def test_thirty_eighth_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1278)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8815)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
