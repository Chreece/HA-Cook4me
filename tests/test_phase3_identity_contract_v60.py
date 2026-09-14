from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog_v60 as builder  # noqa: E402
import release_catalog_phase3_identity_v60 as phase3  # noqa: E402


class Phase3IdentityContractV60Tests(unittest.TestCase):
    def _raw_keyless(self) -> dict:
        return {
            "food": {},
            "quantity": 2,
            "unit": {
                "key": "UNIT_TABLESPOON",
                "name": "Esslöffel",
                "pluralName": "Esslöffel",
                "abbreviation": "EL",
            },
            # Phase 3 deliberately prefers applianceDescription over
            # applicationDescription for a keyless line.
            "applianceDescription": "2 EL gehackte Petersilie",
            "applicationDescription": "2 EL SHOULD NOT WIN",
        }

    def test_live_source_name_is_exact_phase3_source_name(self):
        raw = self._raw_keyless()
        legacy = phase3.crawl_v2._clean_ingredient(raw)
        self.assertIsNotNone(legacy)
        historical, _changed, _field = (
            phase3.assembly_v2._semantic_ingredient_name_with_source(legacy)
        )
        self.assertEqual(historical, "gehackte Petersilie")
        self.assertEqual(phase3.phase3_semantic_source_name(raw), historical)

    def test_capture_wrapper_retains_reviewed_name_before_v59_compaction(self):
        raw = self._raw_keyless()

        def original_extract(root):
            item = root["ingredients"][0]
            return [
                {
                    "name": item["applicationDescription"],
                    "applicationDescription": item["applicationDescription"],
                    "applianceDescription": item["applianceDescription"],
                    "quantity": item["quantity"],
                    "unit": "EL",
                }
            ]

        extract = phase3._augmented_extractor(original_extract)
        rows = extract({"ingredients": [raw]})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "2 EL SHOULD NOT WIN")
        self.assertEqual(rows[0]["semanticSourceName"], "gehackte Petersilie")

        def original_compact(item, ingredients, *, source_language=""):
            return {
                "originalName": item["name"],
                "originalLanguage": source_language,
            }

        compact = phase3._augmented_compactor(original_compact)
        row = compact(rows[0], {}, source_language="de")
        self.assertEqual(row["originalName"], "2 EL SHOULD NOT WIN")
        self.assertEqual(row["semanticSourceName"], "gehackte Petersilie")

    def test_facade_hashes_semantic_source_name_not_display_fallback(self):
        raw = self._raw_keyless()
        historical = phase3.phase3_semantic_source_name(raw)
        expected = builder._core.semantics.source_local_ingredient_id(
            "de", historical
        )
        payload = {
            "row": {
                "semanticSourceName": historical,
                "originalName": "2 EL SHOULD NOT WIN",
            }
        }

        original_enrich = builder._core.enrich_payload
        original_refresh = builder._refresh_safety
        try:
            def fake_enrich(value, _semantic):
                source = builder._core._source_name(value["row"])
                return {
                    "capturedId": builder._core.semantics.source_local_ingredient_id(
                        "de", source
                    )
                }

            builder._core.enrich_payload = fake_enrich
            builder._refresh_safety = lambda result: result
            result = builder.enrich_payload(payload, {})
        finally:
            builder._core.enrich_payload = original_enrich
            builder._refresh_safety = original_refresh

        self.assertEqual(result["capturedId"], expected)
        self.assertNotEqual(
            result["capturedId"],
            builder._core.semantics.source_local_ingredient_id(
                "de", "2 EL SHOULD NOT WIN"
            ),
        )

    def test_capture_patch_is_always_restored(self):
        def original_extract(_root):
            return []

        def original_compact(_item, _ingredients, *, source_language=""):
            return {"sourceLanguage": source_language}

        fake_v59 = SimpleNamespace(
            catalog=SimpleNamespace(extract_recipe_ingredients=original_extract),
            _compact_variant_ingredient=original_compact,
        )

        with self.assertRaisesRegex(RuntimeError, "boom"):
            with phase3.phase3_identity_capture(fake_v59):
                self.assertIsNot(
                    fake_v59.catalog.extract_recipe_ingredients,
                    original_extract,
                )
                self.assertIsNot(
                    fake_v59._compact_variant_ingredient,
                    original_compact,
                )
                raise RuntimeError("boom")

        self.assertIs(fake_v59.catalog.extract_recipe_ingredients, original_extract)
        self.assertIs(fake_v59._compact_variant_ingredient, original_compact)

    def test_provider_backed_line_never_gets_source_local_semantic_name(self):
        raw = self._raw_keyless()
        raw["food"] = {"key": "MARKETINGFOOD_510004", "name": "Parsley"}

        def original_extract(_root):
            return [{"foodKey": "MARKETINGFOOD_510004", "name": "Parsley"}]

        rows = phase3._augmented_extractor(original_extract)(
            {"ingredients": [raw]}
        )
        self.assertEqual(rows, [{"foodKey": "MARKETINGFOOD_510004", "name": "Parsley"}])


if __name__ == "__main__":
    unittest.main()
