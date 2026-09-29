from __future__ import annotations

import errno
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "custom_components" / "cook4me" / "catalog_storage.py"

spec = importlib.util.spec_from_file_location("cook4me_catalog_storage_v250_test", MODULE_PATH)
assert spec is not None and spec.loader is not None
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


class CatalogRuntimeStorageTests(unittest.TestCase):
    def test_promotes_packaged_catalog_and_replaces_previous_runtime_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "installed" / "custom_components" / "cook4me" / "catalog" / "merged_catalog.v1.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b'{"catalogVersion":"new"}')
            target = storage.runtime_catalog_path(root / "config")
            target.parent.mkdir(parents=True)
            target.write_bytes(b'{"catalogVersion":"old"}')

            resolved = storage.prepare_release_catalog_storage(
                root / "config", packaged_path=source
            )

            self.assertEqual(resolved, target)
            self.assertFalse(source.exists())
            self.assertEqual(target.read_bytes(), b'{"catalogVersion":"new"}')


    def test_promotes_compressed_release_catalog_and_removes_stale_raw_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "installed" / "custom_components" / "cook4me" / "catalog" / "merged_catalog.v1.json"
            source.parent.mkdir(parents=True)
            source_gz = Path(str(source) + ".gz")
            source_gz.write_bytes(b"compressed-new")
            target = storage.runtime_catalog_path(root / "config")
            target.parent.mkdir(parents=True)
            target.write_bytes(b"stale-raw")

            resolved = storage.prepare_release_catalog_storage(
                root / "config", packaged_path=source
            )

            target_gz = Path(str(target) + ".gz")
            self.assertEqual(resolved, target)
            self.assertFalse(source_gz.exists())
            self.assertFalse(target.exists())
            self.assertEqual(target_gz.read_bytes(), b"compressed-new")

    def test_existing_compressed_runtime_catalog_is_used_after_promotion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "missing" / "merged_catalog.v1.json"
            target = storage.runtime_catalog_path(root / "config")
            target_gz = Path(str(target) + ".gz")
            target_gz.parent.mkdir(parents=True)
            target_gz.write_bytes(b"persistent-gzip")

            resolved = storage.prepare_release_catalog_storage(
                root / "config", packaged_path=source
            )

            self.assertEqual(resolved, target)
            self.assertFalse(target.exists())
            self.assertEqual(target_gz.read_bytes(), b"persistent-gzip")

    def test_existing_runtime_catalog_is_used_when_package_is_already_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "missing" / "merged_catalog.v1.json"
            target = storage.runtime_catalog_path(root / "config")
            target.parent.mkdir(parents=True)
            target.write_text("persistent", encoding="utf-8")

            resolved = storage.prepare_release_catalog_storage(
                root / "config", packaged_path=source
            )

            self.assertEqual(resolved, target)
            self.assertEqual(target.read_text(encoding="utf-8"), "persistent")

    def test_cross_device_fallback_copies_then_removes_packaged_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "installed" / "merged_catalog.v1.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"catalog")
            target = storage.runtime_catalog_path(root / "config")
            real_replace = os.replace
            calls = 0

            def replace_with_first_exdev(src, dst):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise OSError(errno.EXDEV, "cross-device")
                return real_replace(src, dst)

            with patch.object(storage.os, "replace", side_effect=replace_with_first_exdev):
                resolved = storage.prepare_release_catalog_storage(
                    root / "config", packaged_path=source
                )

            self.assertEqual(resolved, target)
            self.assertFalse(source.exists())
            self.assertEqual(target.read_bytes(), b"catalog")
            self.assertEqual(calls, 2)

    def test_git_checkout_is_not_mutated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "HA-Cook4me"
            (root / ".git").mkdir(parents=True)
            (root / "hacs.json").write_text("{}", encoding="utf-8")
            source = root / "custom_components" / "cook4me" / "catalog" / "merged_catalog.v1.json"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"tracked")
            config = Path(directory) / "config"

            resolved = storage.prepare_release_catalog_storage(
                config, packaged_path=source
            )

            self.assertEqual(resolved, source)
            self.assertTrue(source.exists())
            self.assertFalse(storage.runtime_catalog_path(config).exists())

    def test_wiring_prepares_storage_before_background_catalog_warmup(self):
        init_source = (ROOT / "custom_components" / "cook4me" / "__init__.py").read_text(
            encoding="utf-8"
        )
        runtime_source = (
            ROOT / "custom_components" / "cook4me" / "catalog_runtime.py"
        ).read_text(encoding="utf-8")
        release_source = (
            ROOT / "custom_components" / "cook4me" / "release_catalog.py"
        ).read_text(encoding="utf-8")

        self.assertIn("start_catalog_warmup(hass)", init_source)
        self.assertNotIn("prepare_release_catalog_storage, config_dir", init_source)
        prepare_at = runtime_source.index("prepare_release_catalog_storage, config_dir")
        path_at = runtime_source.index("set_release_catalog_path(catalog_path)")
        warm_at = runtime_source.index("await async_warm_release_catalog(hass)")
        stock_at = runtime_source.index("warm_stock_catalog, payload")
        self.assertLess(prepare_at, path_at)
        self.assertLess(path_at, warm_at)
        self.assertLess(warm_at, stock_at)
        self.assertIn("def set_release_catalog_path(path: str | Path)", release_source)
        self.assertIn("_core._legacy._CATALOG_PATH = target", release_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
