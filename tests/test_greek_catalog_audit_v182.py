from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV182Tests(unittest.TestCase):
    def test_thirty_seventh_pass_cleans_noodle_terminology(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "glass noodle":"Διάφανα νουντλς (glass noodles)",
            "dried glass noodle":"Αποξηραμένα διάφανα νουντλς (glass noodles)",
            "konjac noodle":"Νουντλς σιρατάκι / κόντζακ (shirataki / konjac)",
            "boiled somen noodle":"Βρασμένα νουντλς σόμεν (somen)",
            "ramen noodle":"Νουντλς ράμεν (ramen)",
            "udon noodle":"Νουντλς ούντον (udon)",
            "fresh udon noodle":"Φρέσκα νουντλς ούντον (udon)",
            "package of pre-cooked udon noodle":"Συσκευασία προμαγειρεμένων νουντλς ούντον (udon)",
            "shelled cardamom pods":"Σπόροι κακουλέ χωρίς λοβό",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)

    def test_revised_labels_are_searchable(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        for key in (
            "glass noodle","dried glass noodle","konjac noodle","boiled somen noodle",
            "ramen noodle","udon noodle","fresh udon noodle",
            "package of pre-cooked udon noodle","shelled cardamom pods",
        ):
            aliases={str(value).strip().casefold() for value in data["searchAliases"][key]}
            self.assertIn(key.casefold(),aliases,key)
            self.assertIn(data["labels"][key].casefold(),aliases,key)

    def test_thirty_seventh_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1278)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8800)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
