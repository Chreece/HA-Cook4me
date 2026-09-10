#!/usr/bin/env python3
"""Temporary maintenance patch for cross-catalog provider variant-ID guards."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

crawler_path = ROOT / "tools" / "crawl_release_catalog_v2.py"
crawler = crawler_path.read_text(encoding="utf-8")
marker = "\ndef _cached_state(conn: sqlite3.Connection, variant_id: str) -> str:\n"
helper = '''\ndef _assert_global_variant_ids_unique(conn: sqlite3.Connection) -> None:\n    \"\"\"Fail if one provider variant ID is present in multiple catalog mappings.\"\"\"\n    conflicts = conn.execute(\n        \"SELECT variant_id, COUNT(*), GROUP_CONCAT(language || '/GS_' || country, ',') \"\n        \"FROM catalog_variants GROUP BY variant_id HAVING COUNT(*) > 1 \"\n        \"ORDER BY variant_id LIMIT 20\"\n    ).fetchall()\n    if conflicts:\n        sample = \"; \".join(\n            f\"{variant_id} [{catalogs}]\" for variant_id, _count, catalogs in conflicts\n        )\n        raise RuntimeError(\n            \"provider variant identity is reused across catalog mappings; \"\n            \"global detail identity is no longer safe: \" + sample\n        )\n\n'''
if helper.strip() not in crawler:
    if marker not in crawler:
        raise SystemExit("crawler cached-state marker not found")
    crawler = crawler.replace(marker, helper + marker, 1)
call_marker = '''            _replace_catalog(conn, language, country, rows)\n\n        pending: dict[str, str] = {}\n'''
call_replacement = '''            _replace_catalog(conn, language, country, rows)\n\n        _assert_global_variant_ids_unique(conn)\n\n        pending: dict[str, str] = {}\n'''
if call_marker not in crawler:
    raise SystemExit("crawler pending marker not found")
crawler = crawler.replace(call_marker, call_replacement, 1)
crawler_path.write_text(crawler, encoding="utf-8")

builder_path = ROOT / "tools" / "build_release_catalog.py"
builder = builder_path.read_text(encoding="utf-8")
marker = "\ndef _detail(\n"
helper = '''\ndef _claim_global_variant_ids(\n    seen: dict[str, str], variant_ids: list[str], catalog_label: str\n) -> None:\n    \"\"\"Fail if a provider variant ID is reused by another catalog mapping.\"\"\"\n    for raw in variant_ids:\n        variant_id = _text(raw)\n        if not variant_id:\n            continue\n        previous = seen.get(variant_id)\n        if previous and previous != catalog_label:\n            raise RuntimeError(\n                \"provider variant identity is reused across catalog mappings; \"\n                f\"{variant_id} appears in {previous} and {catalog_label}\"\n            )\n        seen[variant_id] = catalog_label\n\n'''
if helper.strip() not in builder:
    if marker not in builder:
        raise SystemExit("builder detail marker not found")
    builder = builder.replace(marker, helper + marker, 1)
init_marker = '''    all_variants: dict[str, dict[str, Any]] = {}\n    stats: list[dict[str, Any]] = []\n\n    for language, country in AUDITED_CATALOGS:\n'''
init_replacement = '''    all_variants: dict[str, dict[str, Any]] = {}\n    stats: list[dict[str, Any]] = []\n    variant_catalogs: dict[str, str] = {}\n\n    for language, country in AUDITED_CATALOGS:\n'''
if init_marker not in builder:
    raise SystemExit("builder initialization marker not found")
builder = builder.replace(init_marker, init_replacement, 1)
unique_marker = '''        unique = {\n            _text(row.get("searchVariantId")): row\n            for row in search_rows\n            if _text(row.get("searchVariantId"))\n        }\n        hydrated = 0\n'''
unique_replacement = '''        unique = {\n            _text(row.get("searchVariantId")): row\n            for row in search_rows\n            if _text(row.get("searchVariantId"))\n        }\n        _claim_global_variant_ids(\n            variant_catalogs, list(unique), f"{language}/GS_{country}"\n        )\n        hydrated = 0\n'''
if unique_marker not in builder:
    raise SystemExit("builder unique marker not found")
builder = builder.replace(unique_marker, unique_replacement, 1)
builder_path.write_text(builder, encoding="utf-8")

test_path = ROOT / "tests" / "test_release_catalog_global_variant_guard_v59.py"
test_path.write_text('''from __future__ import annotations\n\nimport importlib.util\nfrom pathlib import Path\nimport sys\nimport tempfile\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\n\ndef _load(name: str, path: Path):\n    spec = importlib.util.spec_from_file_location(name, path)\n    assert spec and spec.loader\n    module = importlib.util.module_from_spec(spec)\n    sys.modules[name] = module\n    spec.loader.exec_module(module)\n    return module\n\ncrawler = _load("catalog_guard_crawler", ROOT / "tools" / "crawl_release_catalog_v2.py")\nbuilder = _load("catalog_guard_builder", ROOT / "tools" / "build_release_catalog.py")\n\n\nclass GlobalVariantIdentityGuardTests(unittest.TestCase):\n    def test_crawler_rejects_cross_catalog_variant_id_reuse(self):\n        with tempfile.TemporaryDirectory() as tmp:\n            conn = crawler._open_db(Path(tmp) / "cache.sqlite3")\n            try:\n                crawler._replace_catalog(conn, "de", "DE", [{"variantId": "100"}])\n                crawler._replace_catalog(conn, "en", "GB", [{"variantId": "100"}])\n                with self.assertRaisesRegex(RuntimeError, "reused across catalog mappings"):\n                    crawler._assert_global_variant_ids_unique(conn)\n            finally:\n                conn.close()\n\n    def test_crawler_accepts_globally_unique_variant_ids(self):\n        with tempfile.TemporaryDirectory() as tmp:\n            conn = crawler._open_db(Path(tmp) / "cache.sqlite3")\n            try:\n                crawler._replace_catalog(conn, "de", "DE", [{"variantId": "100"}])\n                crawler._replace_catalog(conn, "en", "GB", [{"variantId": "200"}])\n                crawler._assert_global_variant_ids_unique(conn)\n            finally:\n                conn.close()\n\n    def test_legacy_builder_rejects_cross_catalog_variant_id_reuse(self):\n        seen: dict[str, str] = {}\n        builder._claim_global_variant_ids(seen, ["100", "200"], "de/GS_DE")\n        with self.assertRaisesRegex(RuntimeError, "reused across catalog mappings"):\n            builder._claim_global_variant_ids(seen, ["100"], "en/GS_GB")\n\n    def test_legacy_builder_accepts_repeat_claim_within_same_mapping(self):\n        seen: dict[str, str] = {}\n        builder._claim_global_variant_ids(seen, ["100"], "de/GS_DE")\n        builder._claim_global_variant_ids(seen, ["100"], "de/GS_DE")\n        self.assertEqual({"100": "de/GS_DE"}, seen)\n\n\nif __name__ == "__main__":\n    unittest.main()\n''', encoding="utf-8")
