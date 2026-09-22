from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
FRONTEND=ROOT/"custom_components"/"cook4me"/"frontend"
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV178Tests(unittest.TestCase):
    def test_v178_is_active_and_versioned(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        ui=(FRONTEND/"cook4me-panel-v178.js").read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v179",panel)
        self.assertIn("cook4me-panel-v179.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.6",panel)
        self.assertIn("?v=2026.9.22.6",panel)
        self.assertIn('"version": "2026.9.22.6"',manifest)
        self.assertIn("cook4me-panel-v177.js?v=2026.9.22.4",ui)

    def test_semantic_form_and_purpose_repairs(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        labels=data["labels"]
        expected={
            "large ganmodoki fried tofu":"Μεγάλο Ganmodoki (τηγανητό τόφου με λαχανικά)",
            "romanesco broccoli floret":"Μπουκετάκι κουνουπιδιού ρομανέσκο",
            "small romanesco broccoli floret":"Μικρό μπουκετάκι κουνουπιδιού ρομανέσκο",
            "leek stalk":"Κοτσάνι πράσου",
            "leek stem":"Μίσχος πράσου",
            "head of bok choy":"Κεφάλι πακ τσόι (pak choi / bok choy)",
            "small lamb knuckle-ends":"Μικρά άκρα αρνίσιου κοτσιού",
            "fish sauce for meat":"Σάλτσα ψαριού για κρέας",
            "salad onion stalk":"Κοτσάνι φρέσκου κρεμμυδιού για σαλάτα",
            "roasted buckwheat for kasha":"Καβουρδισμένο φαγόπυρο για κάσα",
            "scampi with tails":"Καραβίδες scampi με ουρές",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)

    def test_puree_and_quantity_semantics_are_not_collapsed(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        labels=data["labels"]
        expected={
            "almond puree":"Πουρές αμυγδάλου",
            "hazelnut puree":"Πουρές φουντουκιού",
            "unsweetened hazelnut puree":"Πουρές φουντουκιού χωρίς ζάχαρη",
            "large slices of rustic baguette":"Μεγάλες φέτες χωριάτικης μπαγκέτας",
            "beef slices, 130 g each":"Φέτες μοσχαριού, 130 g η καθεμία",
            "whole spices: 1 cinnamon stick, 2 bay leaves, 5 cardamom pods":"Ολόκληρα μπαχαρικά: 1 ξυλάκι κανέλας, 2 φύλλα δάφνης, 5 λοβοί κακουλέ",
            "whole spices: 4 cardamom pods, 1 cinnamon stick, 2 bay leaf":"Ολόκληρα μπαχαρικά: 4 λοβοί κακουλέ, 1 ξυλάκι κανέλας, 2 φύλλα δάφνης",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)
        self.assertNotEqual(labels["almond puree"],labels.get("almond paste"))
        self.assertNotEqual(labels["hazelnut puree"],labels.get("hazelnut paste"))

    def test_new_display_labels_are_searchable(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        aliases=data["searchAliases"]
        for key in (
            "romanesco broccoli floret","small romanesco broccoli floret","leek stalk",
            "leek stem","head of bok choy","small lamb knuckle-ends","almond puree",
            "hazelnut puree","beef slices, 130 g each","fish sauce for meat",
        ):
            label=data["labels"][key]
            normalized={str(value).strip().casefold() for value in aliases[key]}
            self.assertIn(key.casefold(),normalized,key)
            self.assertIn(label.casefold(),normalized,key)

    def test_thirty_third_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1273)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8773)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
