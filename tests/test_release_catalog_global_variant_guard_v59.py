from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

crawler = _load("catalog_guard_crawler", ROOT / "tools" / "crawl_release_catalog_v2.py")
builder = _load("catalog_guard_builder", ROOT / "tools" / "build_release_catalog.py")


class GlobalVariantIdentityGuardTests(unittest.TestCase):
    def test_crawler_rejects_cross_catalog_variant_id_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = crawler._open_db(Path(tmp) / "cache.sqlite3")
            try:
                crawler._replace_catalog(conn, "de", "DE", [{"variantId": "100"}])
                crawler._replace_catalog(conn, "en", "GB", [{"variantId": "100"}])
                with self.assertRaisesRegex(RuntimeError, "reused across catalog mappings"):
                    crawler._assert_global_variant_ids_unique(conn)
            finally:
                conn.close()

    def test_crawler_accepts_globally_unique_variant_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            conn = crawler._open_db(Path(tmp) / "cache.sqlite3")
            try:
                crawler._replace_catalog(conn, "de", "DE", [{"variantId": "100"}])
                crawler._replace_catalog(conn, "en", "GB", [{"variantId": "200"}])
                crawler._assert_global_variant_ids_unique(conn)
            finally:
                conn.close()

    def test_legacy_builder_rejects_cross_catalog_variant_id_reuse(self):
        seen: dict[str, str] = {}
        builder._claim_global_variant_ids(seen, ["100", "200"], "de/GS_DE")
        with self.assertRaisesRegex(RuntimeError, "reused across catalog mappings"):
            builder._claim_global_variant_ids(seen, ["100"], "en/GS_GB")

    def test_legacy_builder_accepts_repeat_claim_within_same_mapping(self):
        seen: dict[str, str] = {}
        builder._claim_global_variant_ids(seen, ["100"], "de/GS_DE")
        builder._claim_global_variant_ids(seen, ["100"], "de/GS_DE")
        self.assertEqual({"100": "de/GS_DE"}, seen)


if __name__ == "__main__":
    unittest.main()
