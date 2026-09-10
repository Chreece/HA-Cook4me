from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

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


    def test_export_projects_historical_cache_onto_current_search_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conn = crawler._open_db(root / "cache.sqlite3")
            try:
                # First attempt cached two variants. Variant 100 disappears from
                # the provider search on the retry; its successful detail must
                # remain reusable in SQLite but must not leak into retry output.
                crawler._replace_catalog(
                    conn,
                    "de",
                    "DE",
                    [
                        {"variantId": "100", "title": "Historical", "language": "de", "market": "GS_DE"},
                        {"variantId": "200", "title": "Current detail", "language": "de", "market": "GS_DE"},
                    ],
                )
                crawler._store_result(
                    conn,
                    "detail",
                    "100",
                    {"variantId": "100", "title": "Historical", "language": "de", "market": "GS_DE"},
                )
                crawler._store_result(
                    conn,
                    "detail",
                    "200",
                    {"variantId": "200", "title": "Current detail", "language": "de", "market": "GS_DE"},
                )
                crawler._store_result(
                    conn,
                    "stale404",
                    "999",
                    {"variantId": "999", "standardStatus": 404, "applianceGroupStatus": 404},
                )

                # Retry search changes: 100 vanished; 300 appeared and is a
                # provider-search-only stale row. Historical 100 and 999 stay in
                # cache but are outside the current manifest.
                crawler._replace_catalog(
                    conn,
                    "de",
                    "DE",
                    [
                        {"variantId": "200", "title": "Current detail", "language": "de", "market": "GS_DE"},
                        {"variantId": "300", "title": "Current stale", "language": "de", "market": "GS_DE"},
                    ],
                )
                crawler._store_result(
                    conn,
                    "stale404",
                    "300",
                    {"variantId": "300", "standardStatus": 404, "applianceGroupStatus": 404},
                )

                output = root / "capture.json.gz"
                capture = crawler._export(conn, output)
                self.assertEqual(["200"], [row["variantId"] for row in capture["details"]])
                self.assertEqual(["300"], [row["variantId"] for row in capture["staleSearchOnly"]])
                catalog = capture["source"]["catalogs"][0]
                self.assertEqual(2, catalog["searchRows"])
                self.assertEqual(1, catalog["hydratedVariants"])
                self.assertEqual(1, catalog["staleSearchOnlyVariants"])
                self.assertEqual(0, catalog["unresolvedVariants"])
                self.assertEqual(
                    catalog["searchRows"],
                    len(capture["details"]) + len(capture["staleSearchOnly"]),
                )

                # The cache itself remains resumable: history is retained but
                # the capture is a projection, not a dump of all cache history.
                self.assertIsNotNone(
                    conn.execute("SELECT 1 FROM variant_details WHERE variant_id='100'").fetchone()
                )
                self.assertIsNotNone(
                    conn.execute("SELECT 1 FROM stale_variants WHERE variant_id='999'").fetchone()
                )
            finally:
                conn.close()


    def test_release_crawl_uses_proven_single_page_size(self):
        self.assertEqual(5000, crawler.PAGE_SIZE)
        payload = {
            "content": [
                {"identifier": {"functionalId": "100"}, "title": "One", "lang": "de", "market": "GS_DE"},
                {"identifier": {"functionalId": "200"}, "title": "Two", "lang": "de", "market": "GS_DE"},
            ],
            "page": {"number": 0, "size": 5000, "totalElements": 2, "totalPages": 1},
        }
        with patch.object(crawler, "_headers", return_value=[]), patch.object(
            crawler.catalog, "_http_json", return_value=(payload, "app")
        ) as request:
            rows = crawler._search_catalog(
                {"platform_base_url": "https://example.invalid"}, {}, {},
                language="de", country="DE", configured_language="de", configured_country="DE"
            )
        self.assertEqual(["100", "200"], [row["variantId"] for row in rows])
        self.assertEqual(5000, request.call_args.kwargs["params"]["size"])
        self.assertEqual(0, request.call_args.kwargs["params"]["page"])

    def test_release_crawl_fails_if_single_page_contract_is_exceeded(self):
        payload = {"content": [], "page": {"number": 0, "size": 5000, "totalElements": 5001, "totalPages": 2}}
        with patch.object(crawler, "_headers", return_value=[]), patch.object(
            crawler.catalog, "_http_json", return_value=(payload, "app")
        ):
            with self.assertRaisesRegex(RuntimeError, "exceeds proven single-page"):
                crawler._search_catalog(
                    {"platform_base_url": "https://example.invalid"}, {}, {},
                    language="de", country="DE", configured_language="de", configured_country="DE"
                )

    def test_release_crawl_fails_on_total_or_identity_drift(self):
        mismatch = {
            "content": [{"identifier": {"functionalId": "100"}}],
            "page": {"number": 0, "size": 5000, "totalElements": 2, "totalPages": 1},
        }
        with patch.object(crawler, "_headers", return_value=[]), patch.object(
            crawler.catalog, "_http_json", return_value=(mismatch, "app")
        ):
            with self.assertRaisesRegex(RuntimeError, "row count does not match"):
                crawler._search_catalog(
                    {"platform_base_url": "https://example.invalid"}, {}, {},
                    language="de", country="DE", configured_language="de", configured_country="DE"
                )
        duplicate = {
            "content": [
                {"identifier": {"functionalId": "100"}},
                {"identifier": {"functionalId": "100"}},
            ],
            "page": {"number": 0, "size": 5000, "totalElements": 2, "totalPages": 1},
        }
        with patch.object(crawler, "_headers", return_value=[]), patch.object(
            crawler.catalog, "_http_json", return_value=(duplicate, "app")
        ):
            with self.assertRaisesRegex(RuntimeError, "duplicate provider functional IDs"):
                crawler._search_catalog(
                    {"platform_base_url": "https://example.invalid"}, {}, {},
                    language="de", country="DE", configured_language="de", configured_country="DE"
                )


if __name__ == "__main__":
    unittest.main()
