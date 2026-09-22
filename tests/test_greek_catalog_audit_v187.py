from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV187Tests(unittest.TestCase):
    def test_backend_only_audit_keeps_current_frontend_build(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.7",panel)
        self.assertIn('"version": "2026.9.22.7"',manifest)

    def test_forty_second_pass_cleans_remaining_generic_mixed_labels(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
    "yellow wine": "Κίτρινο κρασί (vin jaune, Jura)",
    "vin jaune yellow wine": "Κίτρινο κρασί (vin jaune, Jura)",
    "welsh onion": "Ουαλικό φρέσκο κρεμμύδι (Welsh onion)",
    "spanish mackerel": "Ισπανικό σκουμπρί (Spanish mackerel)",
    "grana cheese shavings": "Φλοίδες τυριού Γκράνα (Grana)",
    "large slices of toasted mafra bread": "Μεγάλες φέτες φρυγανισμένου ψωμιού Μάφρα (Mafra)",
    "ling fish": "Λινγκ (Molva molva)",
    "ling fish fillets, 250 g each": "Φιλέτα λινγκ (Molva molva), 250 g το καθένα",
    "milkfish belly": "Κοιλιά μίλκφις / μπάνγκους (milkfish / bangus)",
    "hairtail fish": "Τριχιούρος (hairtail / cutlassfish, Trichiurus)",
    "head of lettuce or iceberg lettuce": "Κεφάλι μαρουλιού ή άισμπεργκ (iceberg)",
    "packaged cotechino sausage": "Συσκευασμένο λουκάνικο κοτεκίνο (cotechino)",
    "packet of bourbon vanilla sugar": "Φακελάκι ζάχαρης με βανίλια Μπουρμπόν (Bourbon)",
    "packet taco seasoning mix": "Φακελάκι μείγματος καρυκευμάτων τάκο (taco)",
    "dl of white wine for cooking the pumpkin": "Λευκό κρασί για το μαγείρεμα της κολοκύθας (1 dl)",
    "little gem lettuce": "Μαρούλι Λιτλ Τζεμ (Little Gem)"
}
        self.assertEqual(len(expected),16)
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)
            self.assertRegex(value,r"[\u0370-\u03FF]",key)

    def test_old_source_and_new_labels_remain_searchable_without_duplicates(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        legacy={
    "yellow wine": "Vin jaune (κίτρινο κρασί Jura)",
    "vin jaune yellow wine": "Vin jaune (κίτρινο κρασί Jura)",
    "welsh onion": "Φρέσκο κρεμμύδι τύπου Welsh onion",
    "spanish mackerel": "Spanish mackerel (είδος σκουμπριού)",
    "grana cheese shavings": "Φλοίδες τυριού Grana",
    "large slices of toasted mafra bread": "Μεγάλες φέτες φρυγανισμένου ψωμιού Mafra",
    "ling fish": "Ling (Molva molva)",
    "ling fish fillets, 250 g each": "Φιλέτα ling (Molva molva), 250 g το καθένα",
    "milkfish belly": "Κοιλιά milkfish (bangus)",
    "hairtail fish": "Hairtail / cutlassfish (Trichiurus)",
    "head of lettuce or iceberg lettuce": "Κεφάλι μαρουλιού ή iceberg",
    "packaged cotechino sausage": "Συσκευασμένο λουκάνικο cotechino",
    "packet of bourbon vanilla sugar": "Φακελάκι ζάχαρης με βανίλια Bourbon",
    "packet taco seasoning mix": "Φακελάκι μείγματος καρυκευμάτων taco",
    "dl of white wine for cooking the pumpkin": "dl λευκού κρασιού για το μαγείρεμα της κολοκύθας",
    "little gem lettuce": "Μαρούλι Little Gem"
}
        for key,old_label in legacy.items():
            raw=[str(value).strip().casefold() for value in data["searchAliases"][key]]
            aliases=set(raw)
            self.assertIn(key.casefold(),aliases,key)
            self.assertIn(old_label.casefold(),aliases,key)
            self.assertIn(data["labels"][key].casefold(),aliases,key)
            self.assertEqual(len(raw),len(aliases),key)

    def test_forty_second_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1278)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8983)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
