from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV180Tests(unittest.TestCase):
    def test_backend_only_audit_keeps_current_frontend_build(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v178",panel)
        self.assertIn("cook4me-panel-v178.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.5",panel)
        self.assertIn('"version": "2026.9.22.5"',manifest)

    def test_thirty_fifth_pass_preserves_product_form_and_context(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "blanched almond":"Αποφλοιωμένο αμύγδαλο",
            "whole blanched almond":"Ολόκληρο αποφλοιωμένο αμύγδαλο",
            "chilled cottage cheese":"Cottage cheese ψυγείου",
            "chilled cottage cheese portions":"Μερίδες cottage cheese ψυγείου",
            "chilled portions of cottage cheese":"Μερίδες cottage cheese ψυγείου",
            "yellow sea cod fillet":"Φιλέτο μπακαλιάρου της Κίτρινης Θάλασσας",
            "little gem lettuce":"Μαρούλι Little Gem",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)

    def test_little_gem_is_not_collapsed_to_generic_small_lettuce(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        self.assertNotEqual(labels["little gem lettuce"],labels.get("small lettuce"))
        self.assertIn("Little Gem",labels["little gem lettuce"])

    def test_revised_display_labels_are_searchable(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        for key in (
            "blanched almond","whole blanched almond",
            "chilled cottage cheese","chilled cottage cheese portions",
            "chilled portions of cottage cheese","yellow sea cod fillet",
            "little gem lettuce",
        ):
            aliases={str(value).strip().casefold() for value in data["searchAliases"][key]}
            self.assertIn(key.casefold(),aliases,key)
            self.assertIn(data["labels"][key].casefold(),aliases,key)

    def test_thirty_fifth_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1275)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8787)
        self.assertIn("thirty-fifth audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
