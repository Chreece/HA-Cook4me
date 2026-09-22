from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV179Tests(unittest.TestCase):
    def test_backend_only_audit_keeps_current_frontend_build(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v178",panel)
        self.assertIn("cook4me-panel-v178.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.5",panel)
        self.assertIn('"version": "2026.9.22.5"',manifest)

    def test_thirty_fourth_pass_preserves_missing_semantics(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "fine-grain semolina in a salad bowl":"Ψιλό σιμιγδάλι σε σαλατιέρα",
            "gelatin sheet soaked in cold water":"Φύλλο ζελατίνης μουλιασμένο σε κρύο νερό",
            "gelatin sheet softened in cold water":"Φύλλο ζελατίνης μαλακωμένο σε κρύο νερό",
            "large beefsteak tomato":"Μεγάλη ντομάτα beefsteak (σαρκώδης)",
            "baby lettuce":"Τρυφερό μικρό μαρούλι",
            "warm cooked rice":"Ζεστό μαγειρεμένο ρύζι",
            "warm fresh milk":"Ζεστό φρέσκο γάλα",
            "yellow pollock fillet":"Φιλέτο κίτρινου πόλακ (pollock)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)

    def test_revised_display_labels_remain_searchable(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        for key in (
            "fine-grain semolina in a salad bowl",
            "gelatin sheet soaked in cold water",
            "gelatin sheet softened in cold water",
            "large beefsteak tomato",
            "baby lettuce",
            "warm cooked rice",
            "warm fresh milk",
            "yellow pollock fillet",
        ):
            aliases={str(value).strip().casefold() for value in data["searchAliases"][key]}
            self.assertIn(key.casefold(),aliases,key)
            self.assertIn(data["labels"][key].casefold(),aliases,key)

    def test_thirty_fourth_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1274)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8780)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
