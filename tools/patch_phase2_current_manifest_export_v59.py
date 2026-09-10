#!/usr/bin/env python3
"""Temporary maintenance patch for Phase 2 current-manifest cache projection."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    crawler_path = ROOT / "tools" / "crawl_release_catalog_v2.py"
    text = crawler_path.read_text(encoding="utf-8")

    old = '''    details = [json.loads(row[0]) for row in conn.execute("SELECT detail_json FROM variant_details ORDER BY variant_id")]
    stale = []
    for variant_id, evidence_json in conn.execute("SELECT variant_id,evidence_json FROM stale_variants ORDER BY variant_id"):
        search_rows = [
            json.loads(row[0])
            for row in conn.execute(
                "SELECT search_json FROM catalog_variants WHERE variant_id=? ORDER BY language,country",
                (variant_id,),
            )
        ]
        stale.append({"variantId": variant_id, "evidence": json.loads(evidence_json), "searchRows": search_rows})
'''
    new = '''    # The detail/stale tables are a resumable cache and can contain provider
    # variants from an earlier retry whose search manifest has since changed.
    # Export only cache rows that are members of the CURRENT catalog_variants
    # manifest. Keeping historical rows in SQLite preserves retry efficiency;
    # excluding them from the capture preserves the invariant that one capture
    # is a self-consistent snapshot of one search manifest.
    details = [
        json.loads(row[0])
        for row in conn.execute(
            "SELECT vd.detail_json FROM variant_details vd "
            "WHERE EXISTS ("
            "SELECT 1 FROM catalog_variants cv WHERE cv.variant_id=vd.variant_id"
            ") ORDER BY vd.variant_id"
        )
    ]
    stale = []
    for variant_id, evidence_json in conn.execute(
        "SELECT sv.variant_id,sv.evidence_json FROM stale_variants sv "
        "WHERE EXISTS ("
        "SELECT 1 FROM catalog_variants cv WHERE cv.variant_id=sv.variant_id"
        ") ORDER BY sv.variant_id"
    ):
        search_rows = [
            json.loads(row[0])
            for row in conn.execute(
                "SELECT search_json FROM catalog_variants WHERE variant_id=? ORDER BY language,country",
                (variant_id,),
            )
        ]
        stale.append({"variantId": variant_id, "evidence": json.loads(evidence_json), "searchRows": search_rows})
'''
    if old not in text:
        raise SystemExit("export cache block not found")
    text = text.replace(old, new, 1)

    old = '''        capture = _export(conn, Path(args.output).expanduser())
        unresolved = sum(int(row["unresolvedVariants"]) for row in capture["source"]["catalogs"])
        summary = {
'''
    new = '''        capture = _export(conn, Path(args.output).expanduser())
        unresolved = sum(int(row["unresolvedVariants"]) for row in capture["source"]["catalogs"])
        search_rows_total = sum(int(row["searchRows"]) for row in capture["source"]["catalogs"])
        projected_total = len(capture["details"]) + len(capture["staleSearchOnly"]) + unresolved
        if search_rows_total != projected_total:
            raise RuntimeError(
                "current provider manifest does not balance after cache projection: "
                f"search={search_rows_total} details={len(capture['details'])} "
                f"stale={len(capture['staleSearchOnly'])} unresolved={unresolved}"
            )
        summary = {
'''
    if old not in text:
        raise SystemExit("crawl export summary block not found")
    text = text.replace(old, new, 1)
    crawler_path.write_text(text, encoding="utf-8")

    test_path = ROOT / "tests" / "test_release_catalog_v2_crawler.py"
    tests = test_path.read_text(encoding="utf-8")
    marker = '\n\nif __name__ == "__main__":\n    unittest.main()\n'
    addition = r'''

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
'''
    if marker not in tests:
        raise SystemExit("crawler unittest footer not found")
    tests = tests.replace(marker, addition + marker, 1)
    test_path.write_text(tests, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
