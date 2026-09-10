from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_release_catalog.py"


class ProviderIngredientIdentityContractTests(unittest.TestCase):
    def test_builder_never_manufactures_name_based_ingredient_ids(self):
        text = BUILDER.read_text(encoding="utf-8")
        start = text.index("def _ingredient_id(")
        end = text.index("\ndef _fdc_nutrient", start)
        body = text[start:end]
        self.assertNotIn('"name:"', body)
        self.assertIn('return _text(item.get("foodKey") or item.get("key"))', body)

    def test_keyless_lines_are_evidence_not_global_identity(self):
        text = BUILDER.read_text(encoding="utf-8")
        self.assertIn('"providerIngredientIdentityOnly": True', text)
        self.assertIn('"keylessRecipeLinesStoredAsEvidence": True', text)
        start = text.index("def _compact_variant_ingredient(")
        end = text.index("\ndef _compact_variant_row", start)
        body = text[start:end]
        self.assertIn('"originalName": original_name', body)
        self.assertIn('"originalLanguage": original_language', body)
        self.assertNotIn('or original_name\n', body)


if __name__ == "__main__":
    unittest.main()
