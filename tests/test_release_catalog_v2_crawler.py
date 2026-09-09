from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "crawl_release_catalog_v2.py"
spec = importlib.util.spec_from_file_location("crawl_release_catalog_v2", SCRIPT)
assert spec and spec.loader
crawler = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = crawler
spec.loader.exec_module(crawler)


class ReleaseCatalogV2CrawlerTests(unittest.TestCase):
    def test_all_28_mappings_are_reaudited(self):
        self.assertEqual(28, len(crawler.AUDITED_CATALOGS))
        self.assertIn(("el", "GR"), crawler.AUDITED_CATALOGS)
        self.assertIn(("da", "DK"), crawler.AUDITED_CATALOGS)
        self.assertIn(("sv", "SE"), crawler.AUDITED_CATALOGS)

    def test_clean_ingredient_prefers_provider_food_then_appliance_description(self):
        row = crawler._clean_ingredient(
            {
                "fid": {"functionalId": "123", "sourceSystem": "PRO"},
                "applicationDescription": "2 EL Mascarpone",
                "applianceDescription": "Mascarpone",
                "quantity": 2,
                "unit": {"key": "UNIT_12", "abbreviation": "EL"},
                "food": {"key": "M_FOOD_305", "name": "Mascarpone"},
                "weight": {
                    "quantity": 30,
                    "unit": {"key": "UNIT_27", "abbreviation": "g"},
                },
            }
        )
        self.assertEqual("M_FOOD_305", row["foodKey"])
        self.assertEqual("Mascarpone", row["cleanName"])
        self.assertEqual("Mascarpone", row["applianceDescription"])
        self.assertEqual(30.0, row["weight"]["quantity"])
        self.assertEqual("UNIT_27", row["weight"]["unit"]["key"])

        unkeyed = crawler._clean_ingredient(
            {
                "applicationDescription": "0.5 tablespoon vanilla extract",
                "applianceDescription": "Vanilla extract",
                "quantity": 0.5,
            }
        )
        self.assertNotIn("foodKey", unkeyed)
        self.assertEqual("Vanilla extract", unkeyed["cleanName"])

    def test_detail_payload_keeps_local_provider_identity_and_family_evidence_separate(self):
        root = {
            "fid": {"functionalId": "324705", "sourceSystem": "PRO", "version": "1"},
            "groupingId": {"functionalId": "1169171", "sourceSystem": "PRO"},
            "topRecipeId": "1169171",
            "masterRecipe": {"fid": {"functionalId": "1169171", "sourceSystem": "PRO"}},
            "referenceRecipe": {"fid": {"functionalId": "255386", "sourceSystem": "PRO"}},
            "title": "Example",
            "lang": "it",
            "market": "GS_IT",
            "ingredients": [],
        }
        row = crawler._detail_payload(root, "324705", "it")
        self.assertEqual("324705", row["variantId"])
        self.assertEqual("1169171", row["groupingFunctionalId"])
        self.assertEqual("1169171", row["topRecipeId"])
        self.assertEqual("1169171", row["masterRecipeFunctionalId"])
        self.assertEqual("255386", row["referenceRecipeFunctionalId"])

    def test_only_all_404_statuses_are_classifiable_as_provider_missing(self):
        exc = RuntimeError("app=HTTP404 | dcp=HTTP404")
        self.assertEqual([404, 404], crawler._status_codes(exc))
        mixed = RuntimeError("app=HTTP404 | dcp=HTTP500")
        self.assertEqual([404, 500], crawler._status_codes(mixed))

    def test_duplicate_search_variants_are_collapsed_before_sqlite_write(self):
        rows = [
            {
                "variantId": "100",
                "title": "First title",
                "language": "ar",
                "market": "GS_AE",
                "cover": "",
            },
            {
                "variantId": "100",
                "title": "Different duplicate title",
                "language": "ar",
                "market": "GS_AE",
                "cover": "https://example.invalid/cover.jpg",
            },
            {
                "variantId": "200",
                "title": "Second recipe",
                "language": "ar",
                "market": "GS_AE",
            },
        ]
        unique, duplicate_count = crawler._dedupe_search_rows(rows)
        self.assertEqual(2, len(unique))
        self.assertEqual(1, duplicate_count)
        first = next(row for row in unique if row["variantId"] == "100")
        self.assertEqual("First title", first["title"])
        self.assertEqual("https://example.invalid/cover.jpg", first["cover"])
        self.assertEqual(1, first["duplicateSearchOccurrences"])

        with tempfile.TemporaryDirectory() as tmp:
            conn = crawler._open_db(Path(tmp) / "cache.sqlite3")
            try:
                crawler._replace_catalog(conn, "ar", "AE", rows)
                stored = conn.execute(
                    "SELECT variant_id, search_json FROM catalog_variants "
                    "WHERE language='ar' AND country='AE' ORDER BY variant_id"
                ).fetchall()
                self.assertEqual(["100", "200"], [row[0] for row in stored])
                payload = json.loads(stored[0][1])
                self.assertEqual(1, payload["duplicateSearchOccurrences"])
                row_count = conn.execute(
                    "SELECT row_count FROM catalog_runs WHERE language='ar' AND country='AE'"
                ).fetchone()[0]
                self.assertEqual(2, row_count)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()
