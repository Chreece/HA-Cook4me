#!/usr/bin/env python3
"""One-shot fail-closed patch for provider-ID-only release ingredient identity."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


path = "tools/build_release_catalog.py"
text = read(path)
text = replace_once(
    text,
    '''def _ingredient_id(item: dict[str, Any]) -> str:\n    explicit = _text(item.get("ingredientId") or item.get("id"))\n    if explicit:\n        return explicit\n    key = _text(item.get("foodKey") or item.get("key"))\n    if key:\n        return key\n    name = _text(\n        item.get("canonicalName")\n        or item.get("foodName")\n        or item.get("name")\n    ).casefold()\n    return "name:" + name if name else ""\n''',
    '''def _ingredient_id(item: dict[str, Any]) -> str:\n    """Return only provider-backed ingredient identity.\n\n    Keyless recipe lines are useful source evidence, but a translated or\n    normalized label is never promoted into a synthetic global ingredient ID.\n    """\n    explicit = _text(item.get("ingredientId") or item.get("id"))\n    if explicit:\n        return explicit\n    return _text(item.get("foodKey") or item.get("key"))\n''',
    "provider-only ingredient identity",
)
text = replace_once(
    text,
    '''    # Canonical identity lives globally. Exact provider wording lives on the\n    # recipe-line reference so native users see what SEB actually published.\n    if not key:\n        row["canonicalName"] = _text(global_row.get("canonicalName")) or original_name\n''',
    '''    # Canonical identity lives only on a provider-backed global row. Keyless\n    # recipe lines retain originalName/originalLanguage as source evidence and do\n    # not invent an English canonical label or a synthetic ingredient identity.\n    if ident and not key:\n        canonical = _text(global_row.get("canonicalName"))\n        if canonical:\n            row["canonicalName"] = canonical\n''',
    "keyless compact ingredient evidence",
)
text = replace_once(
    text,
    '''            "providerNativeNamesStored": True,\n            "applianceGroup":''',
    '''            "providerNativeNamesStored": True,\n            "providerIngredientIdentityOnly": True,\n            "keylessRecipeLinesStoredAsEvidence": True,\n            "applianceGroup":''',
    "release identity policy flags",
)
write(path, text)

Path(ROOT / "tests/test_release_catalog_provider_id_identity_v59.py").write_text(
    '''from pathlib import Path\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\nBUILDER = ROOT / "tools/build_release_catalog.py"\n\n\nclass ProviderIngredientIdentityContractTests(unittest.TestCase):\n    def test_builder_never_manufactures_name_based_ingredient_ids(self):\n        text = BUILDER.read_text(encoding="utf-8")\n        start = text.index("def _ingredient_id(")\n        end = text.index("\\ndef _fdc_nutrient", start)\n        body = text[start:end]\n        self.assertNotIn('"name:"', body)\n        self.assertIn('return _text(item.get("foodKey") or item.get("key"))', body)\n\n    def test_keyless_lines_are_evidence_not_global_identity(self):\n        text = BUILDER.read_text(encoding="utf-8")\n        self.assertIn('"providerIngredientIdentityOnly": True', text)\n        self.assertIn('"keylessRecipeLinesStoredAsEvidence": True', text)\n        start = text.index("def _compact_variant_ingredient(")\n        end = text.index("\\ndef _compact_variant_row", start)\n        body = text[start:end]\n        self.assertIn('"originalName": original_name', body)\n        self.assertIn('"originalLanguage": original_language', body)\n        self.assertNotIn('or original_name\\n', body)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
    encoding="utf-8",
)
