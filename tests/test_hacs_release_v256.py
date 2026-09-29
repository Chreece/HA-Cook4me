"""Compact HACS zip-release payload regressions."""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import posixpath
import re
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "cook4me"
BUILDER = ROOT / "tools" / "build_hacs_release.py"
RAW = COMP / "catalog" / "merged_catalog.v1.json"
GZ_NAME = "catalog/merged_catalog.v1.json.gz"
IMPORTS = re.compile(r'''\b(?:import\s*(?:\(\s*)?|from\s*)["']([^"']+)["']''')
RETIRED = re.compile(r"frontend/cook4me-panel-v(\d+)-bundle\.js$")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_module("cook4me_hacs_release_builder_test", BUILDER)


def sha256_stream(handle) -> str:
    digest = hashlib.sha256()
    while chunk := handle.read(1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def module_closure(files: dict[str, bytes], entry: str) -> set[str]:
    pending, seen = [entry], set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        if path not in files:
            raise AssertionError("Missing release frontend dependency: " + path)
        seen.add(path)
        source = files[path].decode("utf-8")
        for specifier in IMPORTS.findall(source):
            if not specifier.startswith("."):
                continue
            target = posixpath.normpath(
                posixpath.join(
                    posixpath.dirname(path),
                    specifier.split("?", 1)[0].split("#", 1)[0],
                )
            )
            pending.append(target)
    return seen


class HacsReleaseV256Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="cook4me-hacs-release-")
        cls.output = Path(cls.tmp.name) / "cook4me.zip"
        cls.version = "2026.9.28.999999"
        cls.report = builder.build(cls.output, version=cls.version)
        with ZipFile(cls.output) as archive:
            cls.files = {
                item.filename: archive.read(item)
                for item in archive.infolist()
                if not item.is_dir()
            }

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_hacs_manifest_selects_release_asset(self):
        hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))
        self.assertTrue(hacs["zip_release"])
        self.assertEqual(hacs["filename"], "cook4me.zip")
        self.assertTrue(hacs["hide_default_branch"])

    def test_release_zip_is_rooted_at_the_integration(self):
        self.assertIn("manifest.json", self.files)
        self.assertIn("__init__.py", self.files)
        self.assertFalse(any(name.startswith("custom_components/") for name in self.files))
        manifest = json.loads(self.files["manifest.json"])
        self.assertEqual(manifest["version"], self.version)

    def test_release_uses_lossless_compressed_catalog_only(self):
        self.assertNotIn("catalog/merged_catalog.v1.json", self.files)
        self.assertIn(GZ_NAME, self.files)
        source_hash = sha256_stream(RAW.open("rb"))
        compressed_hash = sha256_stream(
            gzip.GzipFile(fileobj=io.BytesIO(self.files[GZ_NAME]), mode="rb")
        )
        self.assertEqual(compressed_hash, source_hash)
        self.assertEqual(self.report["catalogSha256"], source_hash)

    def test_installed_payload_is_materially_smaller_than_current_hacs_path(self):
        old = self.report["legacyInstallBytes"]
        new = self.report["packagedRuntimeBytes"]
        self.assertGreater(old, 80 * 1024 * 1024)
        self.assertLess(new, old * 0.45)
        self.assertGreater(self.report["installedPayloadReductionPercent"], 55)
        self.assertFalse(self.report["rawCatalogIncluded"])
        self.assertTrue(self.report["compressedCatalogIncluded"])
        self.assertEqual(self.report["retiredBundlesIncluded"], 0)

    def test_active_frontend_import_closure_is_complete(self):
        panel = self.files["panel.py"].decode("utf-8")
        entry = re.search(r'^_PANEL_MODULE\s*=\s*["\']([^"\']+)', panel, re.M)
        self.assertIsNotNone(entry)
        closure = module_closure(self.files, "frontend/" + entry.group(1))
        self.assertIn("frontend/" + entry.group(1), closure)
        self.assertFalse(any(RETIRED.fullmatch(path) and int(RETIRED.fullmatch(path).group(1)) < 126 for path in closure))

    def test_generated_concept_substitution_overlay_is_packaged(self):
        name = "catalog/concept_ingredient_substitutions.v1.json"
        self.assertIn(name, self.files)
        payload = json.loads(self.files[name])
        self.assertEqual(payload.get("schemaVersion"), 1)
        bindings = payload.get("ingredientBindings") or []
        self.assertGreaterEqual(len(bindings), 10)
        self.assertGreater(
            sum(len(row.get("conceptIds") or []) for row in bindings),
            1000,
        )
        self.assertTrue(self.report["generatedConceptBindingsIncluded"])
        self.assertGreater(self.report["generatedConceptBindingsBytes"], 10000)

    def test_generated_provider_substitution_overlay_is_packaged(self):
        name = "catalog/provider_ingredient_substitutions.generated.v1.json"
        self.assertIn(name, self.files)
        payload = json.loads(self.files[name])
        self.assertEqual(payload.get("schemaVersion"), 1)
        bindings = payload.get("ingredientBindings") or []
        self.assertTrue(
            any(
                "MARKETINGFOOD_510004" in (row.get("ingredientIds") or [])
                for row in bindings
            )
        )
        self.assertTrue(self.report["generatedProviderBindingsIncluded"])
        self.assertGreater(self.report["generatedProviderBindingsBytes"], 10000)

    def test_runtime_loader_reads_gzip_when_json_is_not_installed(self):
        legacy = load_module(
            "cook4me_release_catalog_legacy_gzip_test",
            COMP / "release_catalog_legacy.py",
        )
        payload = {
            "schemaVersion": 1,
            "catalogVersion": "gzip-test",
            "complete": True,
            "ingredients": [{"id": "salt", "name": "Salt"}],
            "recipes": [],
        }
        with tempfile.TemporaryDirectory(prefix="cook4me-gzip-loader-") as directory:
            raw_path = Path(directory) / "catalog.json"
            with gzip.open(str(raw_path) + ".gz", "wt", encoding="utf-8") as handle:
                json.dump(payload, handle)
            legacy._CATALOG_PATH = raw_path
            legacy.load_release_catalog.cache_clear()
            loaded = legacy.load_release_catalog()
        self.assertEqual(loaded["catalogVersion"], "gzip-test")
        self.assertEqual(loaded["ingredients"][0]["id"], "salt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
