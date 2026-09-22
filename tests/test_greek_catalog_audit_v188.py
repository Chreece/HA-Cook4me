from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"el.json"
CURATED=ROOT/"custom_components"/"cook4me"/"catalog_ui_locales"/"zz_el_curated.json"


class GreekCatalogAuditV188Tests(unittest.TestCase):
    def test_all_reviewed_curated_labels_are_synced_into_base_fallback(self):
        base=json.loads(BASE.read_text(encoding="utf-8"))
        curated=json.loads(CURATED.read_text(encoding="utf-8"))
        reviewed=curated["labels"]
        self.assertGreaterEqual(len(reviewed),1278)
        missing=[]
        mismatched=[]
        for key,value in reviewed.items():
            if key not in base["labels"]:
                missing.append(key)
            elif base["labels"][key]!=value:
                mismatched.append((key,base["labels"][key],value))
        self.assertEqual(missing,[])
        self.assertEqual(mismatched,[])

    def test_base_source_records_reviewed_sync(self):
        data=json.loads(BASE.read_text(encoding="utf-8"))
        self.assertIn("synchronized with curated audit",data["translationSource"])
        self.assertGreaterEqual(len(data["labels"]),3713)


if __name__=="__main__":
    unittest.main()
