from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/"custom_components"/"cook4me"/"panel.py"
MANIFEST=ROOT/"custom_components"/"cook4me"/"manifest.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV188Tests(unittest.TestCase):
    def test_backend_only_audit_keeps_current_frontend_build(self):
        panel=PANEL.read_text(encoding="utf-8")
        manifest=MANIFEST.read_text(encoding="utf-8")
        self.assertIn("cook4me-recipe-hub-panel-v180",panel)
        self.assertIn("cook4me-panel-v180.js",panel)
        self.assertIn("/cook4me_static/2026.9.22.7",panel)
        self.assertIn('"version": "2026.9.22.7"',manifest)

    def test_forty_third_pass_promotes_common_greek_labels(self):
        labels=json.loads(CURATED.read_text(encoding="utf-8"))["labels"]
        expected={
            "sesame oil":"Σησαμέλαιο",
            "pea":"Αρακάς",
            "curry powder":"Κάρι σε σκόνη",
            "maple syrup":"Σιρόπι σφενδάμου",
            "garlic":"Σκόρδο",
            "oil":"Λάδι",
            "coriander":"Κόλιανδρος",
            "coconut":"Καρύδα",
            "parsley":"Μαϊντανός",
            "sesame seed":"Σουσάμι",
            "agave syrup":"Σιρόπι αγαύης",
        }
        for key,value in expected.items():
            self.assertEqual(labels.get(key),value,key)

    def test_promoted_labels_and_source_terms_are_searchable(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        for key in (
            "sesame oil","pea","curry powder","maple syrup","garlic","oil",
            "coriander","coconut","parsley","sesame seed","agave syrup",
        ):
            aliases={str(value).strip().casefold() for value in data["searchAliases"][key]}
            self.assertIn(key.casefold(),aliases,key)
            self.assertIn(data["labels"][key].casefold(),aliases,key)

    def test_forty_third_audit_scope(self):
        data=json.loads(CURATED.read_text(encoding="utf-8"))
        alias_entries=sum(len(values) for values in data["searchAliases"].values())
        self.assertGreaterEqual(len(data["labels"]),1289)
        self.assertEqual(len(data["searchAliases"]),3689)
        self.assertGreaterEqual(alias_entries,8983)
        self.assertIn("audit",data["translationSource"])


if __name__=="__main__":
    unittest.main()
