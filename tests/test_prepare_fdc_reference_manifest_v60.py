from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import prepare_fdc_reference_data_v60 as prepare_fdc  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed_dataset_files(root: Path) -> None:
    for index, dataset in enumerate(prepare_fdc._DATASETS, 1):
        (root / dataset["archiveName"]).write_bytes(f"archive-{index}".encode())
        (root / dataset["jsonName"]).write_text(
            json.dumps({"seed": index}), encoding="utf-8"
        )


class PrepareFdcReferenceManifestV60Tests(unittest.TestCase):
    def test_unchanged_pinned_datasets_reuse_manifest_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_dataset_files(root)

            first_manifest, first_summary = prepare_fdc.prepare(root)
            manifest_path = root / "reference-manifest.v60.json"
            first_bytes = manifest_path.read_bytes()
            first_sha = _sha(manifest_path)

            self.assertFalse(first_summary["referenceManifestReused"])
            self.assertEqual(first_summary["downloadedDatasetCount"], 0)
            self.assertEqual(first_summary["reusedDatasetCount"], 3)
            self.assertEqual(first_summary["referenceManifestSha256"], first_sha)

            second_manifest, second_summary = prepare_fdc.prepare(root)
            self.assertTrue(second_summary["referenceManifestReused"])
            self.assertEqual(second_summary["downloadedDatasetCount"], 0)
            self.assertEqual(second_summary["reusedDatasetCount"], 3)
            self.assertEqual(manifest_path.read_bytes(), first_bytes)
            self.assertEqual(_sha(manifest_path), first_sha)
            self.assertEqual(second_summary["referenceManifestSha256"], first_sha)
            self.assertEqual(second_manifest, first_manifest)

    def test_dataset_byte_change_forces_new_manifest_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_dataset_files(root)
            _manifest, first_summary = prepare_fdc.prepare(root)
            first_sha = first_summary["referenceManifestSha256"]

            foundation_json = root / prepare_fdc._DATASETS[0]["jsonName"]
            foundation_json.write_text(json.dumps({"seed": 1, "changed": True}), encoding="utf-8")

            _manifest, second_summary = prepare_fdc.prepare(root)
            self.assertFalse(second_summary["referenceManifestReused"])
            self.assertEqual(second_summary["downloadedDatasetCount"], 0)
            self.assertEqual(second_summary["reusedDatasetCount"], 3)
            self.assertNotEqual(second_summary["referenceManifestSha256"], first_sha)


if __name__ == "__main__":
    unittest.main()
