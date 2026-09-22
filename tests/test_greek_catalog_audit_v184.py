from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV184Tests(unittest.TestCase):
    def test_backend_only_audit_keeps_current_frontend_build(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.7",panel)
        self.assertIn('"version": "2026.9.22.7"',manifest)

    def test_thirty_ninth_pass_uses_natural_greek_market_labels(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "edamame":"Ενταμάμε (edamame)",
            "young soybeans":"Ενταμάμε (νεαρά φασόλια σόγιας)",
            "edamame bean":"Ενταμάμε (φασόλια σόγιας)",
            "edamame pods":"Ενταμάμε με τον λοβό",
            "kelp":"Φύκια κελπ (kelp)",
            "quick-cook farro":"Φάρρο γρήγορου μαγειρέματος (farro)",
            "job's tears":"Δάκρυα του Ιώβ (σπόροι coix / adlay)",
            "chilled cottage cheese":"Τυρί κότατζ ψυγείου",
            "chilled cottage cheese portions":"Μερίδες τυριού κότατζ ψυγείου",
            "chilled portions of cottage cheese":"Μερίδες τυριού κότατζ ψυγείου",
            "cottage cheese with herbs":"Τυρί κότατζ με μυρωδικά",
            "portions of cottage cheese":"Μερίδες τυριού κότατζ",
            "skyr":"Σκιρ (skyr)",
            "berry skyr":"Σκιρ με μούρα (skyr)",
            "vanilla skyr":"Σκιρ βανίλιας (skyr)",
            "bok choy":"Πακ τσόι (pak choi / bok choy)",
            "pak choi":"Πακ τσόι (pak choi / bok choy)",
            "daikon radish":"Λευκό ραπανάκι ντάικον (daikon)",
            "napa cabbage kimchi":"Κίμτσι με λάχανο νάπα (napa)",
            "sriracha sauce":"Καυτερή σάλτσα σριράτσα (sriracha)",
            "harissa":"Πάστα χαρίσα (harissa)",
            "ponzu":"Σάλτσα πόνζου (ponzu)",
            "ponzu sauce":"Σάλτσα πόνζου (ponzu)",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)

    def test_previous_package_names_and_new_greek_labels_are_searchable(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        legacy={
            "edamame":"Edamame",
            "kelp":"Kelp (φύκια)",
            "quick-cook farro":"Farro γρήγορου μαγειρέματος",
            "skyr":"Skyr (σκιρ)",
            "bok choy":"Pak choi / bok choy (πακ τσόι)",
            "daikon radish":"Daikon (λευκό ραπανάκι)",
            "sriracha sauce":"Sriracha (καυτερή σάλτσα τσίλι)",
            "harissa":"Harissa (πάστα καυτερής πιπεριάς)",
            "ponzu":"Ponzu (ιαπωνική σάλτσα εσπεριδοειδών)",
        }
        for key,old_label in legacy.items():
            aliases={str(value).strip().casefold() for value in data["searchAliases"][key]}
            self.assertIn(key.casefold(),aliases,key)
            self.assertIn(old_label.casefold(),aliases,key)
            self.assertIn(data["labels"][key].casefold(),aliases,key)

    def test_thirty_ninth_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1278)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8838)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
