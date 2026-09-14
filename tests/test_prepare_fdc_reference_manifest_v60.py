from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import prepare_fdc_reference_data_v60 as prepare_fdc  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _test_datasets() -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for index, source in enumerate(prepare_fdc._DATASETS, 1):
        archive = f"archive-{index}".encode()
        json_bytes = json.dumps({"seed": index}).encode()
        row = dict(source)
        row.update(
            {
                "expectedArchiveSha256": hashlib.sha256(archive).hexdigest(),
                "expectedArchiveBytes": len(archive),
                "expectedJsonSha256": hashlib.sha256(json_bytes).hexdigest(),
                "expectedJsonBytes": len(json_bytes),
            }
        )
        rows.append(row)
    return tuple(rows)


def _seed_dataset_files(root: Path, datasets: tuple[dict[str, object], ...]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for index, dataset in enumerate(datasets, 1):
        (root / str(dataset["archiveName"])).write_bytes(f"archive-{index}".encode())
        (root / str(dataset["jsonName"])).write_text(
            json.dumps({"seed": index}), encoding="utf-8"
        )


class PrepareFdcReferenceManifestV60Tests(unittest.TestCase):
    def test_production_dataset_pins_are_well_formed(self):
        self.assertEqual(len(prepare_fdc._DATASETS), 3)
        for dataset in prepare_fdc._DATASETS:
            prepare_fdc._validate_dataset_definition(dataset)
            self.assertTrue(prepare_fdc._valid_sha256(dataset["expectedArchiveSha256"]))
            self.assertTrue(prepare_fdc._valid_sha256(dataset["expectedJsonSha256"]))
            self.assertGreater(dataset["expectedArchiveBytes"], 0)
            self.assertGreater(dataset["expectedJsonBytes"], 0)

    def test_unchanged_pinned_datasets_reuse_manifest_byte_for_byte(self):
        datasets = _test_datasets()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(prepare_fdc, "_DATASETS", datasets):
            root = Path(tmp)
            _seed_dataset_files(root, datasets)

            first_manifest, first_summary = prepare_fdc.prepare(root)
            manifest_path = root / "reference-manifest.v60.json"
            first_bytes = manifest_path.read_bytes()
            first_sha = _sha(manifest_path)

            self.assertFalse(first_summary["referenceManifestReused"])
            self.assertTrue(first_summary["referenceManifestDeterministic"])
            self.assertTrue(first_summary["datasetPinsVerified"])
            self.assertEqual(first_summary["downloadedDatasetCount"], 0)
            self.assertEqual(first_summary["reusedDatasetCount"], 3)
            self.assertEqual(first_summary["referenceManifestSha256"], first_sha)
            self.assertNotIn("generatedAt", first_manifest)
            self.assertTrue(first_manifest["policy"]["manifestContentAddressed"])
            self.assertTrue(first_manifest["policy"]["datasetBytesPinned"])
            self.assertEqual(first_manifest["policy"]["datasetPinAlgorithm"], "SHA-256")
            self.assertFalse(first_manifest["policy"]["runtimeTimestampInManifest"])

            second_manifest, second_summary = prepare_fdc.prepare(root)
            self.assertTrue(second_summary["referenceManifestReused"])
            self.assertEqual(second_summary["downloadedDatasetCount"], 0)
            self.assertEqual(second_summary["reusedDatasetCount"], 3)
            self.assertEqual(manifest_path.read_bytes(), first_bytes)
            self.assertEqual(_sha(manifest_path), first_sha)
            self.assertEqual(second_summary["referenceManifestSha256"], first_sha)
            self.assertEqual(second_manifest, first_manifest)

    def test_independent_workspaces_get_identical_manifest_bytes(self):
        datasets = _test_datasets()
        with (
            tempfile.TemporaryDirectory() as tmp1,
            tempfile.TemporaryDirectory() as tmp2,
            mock.patch.object(prepare_fdc, "_DATASETS", datasets),
        ):
            first = Path(tmp1)
            second = Path(tmp2)
            _seed_dataset_files(first, datasets)
            _seed_dataset_files(second, datasets)

            first_manifest, first_summary = prepare_fdc.prepare(first)
            second_manifest, second_summary = prepare_fdc.prepare(second)

            self.assertEqual(first_manifest, second_manifest)
            self.assertEqual(
                (first / "reference-manifest.v60.json").read_bytes(),
                (second / "reference-manifest.v60.json").read_bytes(),
            )
            self.assertEqual(
                first_summary["referenceManifestSha256"],
                second_summary["referenceManifestSha256"],
            )
            self.assertEqual(first_summary["datasets"], second_summary["datasets"])

    def test_legacy_timestamped_manifest_is_migrated_to_content_addressed_pinned_form(self):
        datasets = _test_datasets()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(prepare_fdc, "_DATASETS", datasets):
            root = Path(tmp)
            _seed_dataset_files(root, datasets)
            rows = [prepare_fdc._existing_valid(root, dataset) for dataset in datasets]
            self.assertTrue(all(row is not None for row in rows))
            legacy = prepare_fdc._manifest_body([row for row in rows if row is not None])
            legacy["generatedAt"] = "2026-09-14T00:00:00+00:00"
            legacy["policy"].pop("datasetBytesPinned", None)
            legacy["policy"].pop("datasetPinAlgorithm", None)
            manifest_path = root / "reference-manifest.v60.json"
            manifest_path.write_text(json.dumps(legacy, indent=2) + "\n", encoding="utf-8")

            manifest, summary = prepare_fdc.prepare(root)
            self.assertFalse(summary["referenceManifestReused"])
            self.assertNotIn("generatedAt", manifest)
            self.assertTrue(manifest["policy"]["datasetBytesPinned"])
            self.assertEqual(
                manifest,
                prepare_fdc._manifest_body([row for row in rows if row is not None]),
            )

    def test_archive_byte_drift_fails_closed_before_extraction(self):
        datasets = _test_datasets()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(prepare_fdc, "_DATASETS", datasets):
            root = Path(tmp)
            _seed_dataset_files(root, datasets)
            first = datasets[0]
            archive = root / str(first["archiveName"])
            archive.write_bytes(b"different-archive-bytes")

            with (
                mock.patch.object(prepare_fdc, "_download", return_value=None),
                mock.patch.object(prepare_fdc, "_extract_json") as extract,
                self.assertRaisesRegex(RuntimeError, "downloaded archive differs from pinned USDA bytes"),
            ):
                prepare_fdc.prepare(root)
            extract.assert_not_called()

    def test_extracted_json_byte_drift_fails_closed(self):
        datasets = _test_datasets()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(prepare_fdc, "_DATASETS", datasets):
            root = Path(tmp)
            _seed_dataset_files(root, datasets)
            first = datasets[0]
            json_path = root / str(first["jsonName"])
            json_path.write_text(json.dumps({"seed": 1, "changed": True}), encoding="utf-8")

            with (
                mock.patch.object(prepare_fdc, "_download", return_value=None),
                mock.patch.object(prepare_fdc, "_extract_json", return_value=None),
                self.assertRaisesRegex(RuntimeError, "extracted reference data differs from pinned USDA bytes"),
            ):
                prepare_fdc.prepare(root)

    def test_invalid_pin_definition_fails_before_network(self):
        datasets = list(_test_datasets())
        broken = dict(datasets[0])
        broken["expectedArchiveSha256"] = "not-a-sha"
        datasets[0] = broken
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(prepare_fdc, "_DATASETS", tuple(datasets)):
            with (
                mock.patch.object(prepare_fdc, "_download") as download,
                self.assertRaisesRegex(RuntimeError, "invalid pinned expectedArchiveSha256"),
            ):
                prepare_fdc.prepare(Path(tmp))
            download.assert_not_called()


if __name__ == "__main__":
    unittest.main()
