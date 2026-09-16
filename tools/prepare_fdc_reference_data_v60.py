#!/usr/bin/env python3
"""Download and byte-pin the USDA FDC reference datasets used by v60 review.

This downloads public USDA archives only. It needs no FDC/data.gov API key and
persists no credential. The pinned releases are Foundation Foods April 2026,
final SR Legacy April 2018, and FNDDS 2021-2023 published October 2024.

The reference manifest is intentionally content-addressed: run timestamps are
excluded, so identical archive/JSON bytes produce identical manifest bytes and
an identical SHA-256 even in fresh CI workspaces.  Each versioned USDA archive
and its extracted JSON are also pinned by SHA-256 and byte length.  If a remote
file is ever replaced behind the same URL, preparation fails closed instead of
silently changing the nutrition evidence corpus.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile
from typing import Any

FOUNDATION_URL = (
    "https://fdc.nal.usda.gov/fdc-datasets/"
    "FoodData_Central_foundation_food_json_2026-04-30.zip"
)
SR_LEGACY_URL = (
    "https://fdc.nal.usda.gov/fdc-datasets/"
    "FoodData_Central_sr_legacy_food_json_2018-04.zip"
)
FNDDS_URL = (
    "https://fdc.nal.usda.gov/fdc-datasets/"
    "FoodData_Central_survey_food_json_2024-10-31.zip"
)
REFERENCE_KIND = "cook4me-fdc-reference-data-v60"

# These pins were captured from a successful public USDA download on 2026-09-14
# after the manifest itself was made deterministic.  Both transport bytes and
# extracted JSON bytes are enforced so archive repacking and data replacement are
# independently detectable.
_DATASETS: tuple[dict[str, Any], ...] = (
    {
        "dataType": "Foundation",
        "releaseDate": "2026-04-30",
        "url": FOUNDATION_URL,
        "archiveName": "foundation-2026-04-30.zip",
        "jsonName": "foundation-2026-04-30.json",
        "zipHint": "foundation",
        "expectedArchiveSha256": "186e988ec542e913f51ef62b86a47758e8cdd0d1dc3889e7b055581f3c09c77a",
        "expectedArchiveBytes": 469303,
        "expectedJsonSha256": "27d1fe3fd89edfbe528ed915da5619320e1d004d4594603a1b19bdb1511590cc",
        "expectedJsonBytes": 6721650,
    },
    {
        "dataType": "SR Legacy",
        "releaseDate": "2018-04",
        "url": SR_LEGACY_URL,
        "archiveName": "sr-legacy-2018-04.zip",
        "jsonName": "sr-legacy-2018-04.json",
        "zipHint": "sr_legacy",
        "expectedArchiveSha256": "0fe8ae486a2c8eb42cb96413f058deb51863a46c8fb8eeb4b1fb45006dd338ef",
        "expectedArchiveBytes": 13456312,
        "expectedJsonSha256": "70d4235ae3a2bdf48a7b9eaa1286a83fa67b6f3270436c9ce8b008213f500129",
        "expectedJsonBytes": 210758826,
    },
    {
        "dataType": "Survey (FNDDS)",
        "releaseDate": "2024-10-31",
        "url": FNDDS_URL,
        "archiveName": "fndds-2021-2023-2024-10-31.zip",
        "jsonName": "fndds-2021-2023-2024-10-31.json",
        "zipHint": "survey",
        "expectedArchiveSha256": "dfb06ae7ddc397ccd570b91c14b75438ab2ba39f64f22d321f61d4a52a77f3eb",
        "expectedArchiveBytes": 3835292,
        "expectedJsonSha256": "2e7eb9fda92adf1d4d784dba5eaa3a7fd4418cd86ccff383c7c9294d79e9b808",
        "expectedJsonBytes": 66294426,
    },
)

_PIN_FIELDS = (
    ("archiveSha256", "expectedArchiveSha256"),
    ("archiveBytes", "expectedArchiveBytes"),
    ("jsonSha256", "expectedJsonSha256"),
    ("jsonBytes", "expectedJsonBytes"),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _validate_dataset_definition(dataset: dict[str, Any]) -> None:
    label = str(dataset.get("dataType") or "dataset")
    for key in ("expectedArchiveSha256", "expectedJsonSha256"):
        if not _valid_sha256(dataset.get(key)):
            raise RuntimeError(f"{label}: invalid pinned {key}")
    for key in ("expectedArchiveBytes", "expectedJsonBytes"):
        value = dataset.get(key)
        if type(value) is not int or value <= 0:
            raise RuntimeError(f"{label}: invalid pinned {key}")


def _download(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "HA-Cook4me-FDC-reference-v60/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
            shutil.copyfileobj(response, handle, length=1024 * 1024)
        temporary.replace(output)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _extract_json(archive: Path, output: Path, hint: str) -> None:
    with zipfile.ZipFile(archive) as zf:
        candidates = [name for name in zf.namelist() if name.lower().endswith(".json")]
        if not candidates:
            raise RuntimeError(f"{archive}: no JSON member found")
        preferred = [name for name in candidates if hint in name.casefold()]
        chosen = sorted(preferred or candidates, key=lambda name: (len(name), name))[0]
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".part")
        try:
            with zf.open(chosen) as source, temporary.open("wb") as destination:
                shutil.copyfileobj(source, destination, length=1024 * 1024)
            value = json.loads(temporary.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise RuntimeError(f"{archive}: extracted FDC JSON is not an object")
            temporary.replace(output)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _observed_dataset(output_dir: Path, dataset: dict[str, Any]) -> dict[str, Any] | None:
    archive = output_dir / dataset["archiveName"]
    json_path = output_dir / dataset["jsonName"]
    if not archive.is_file() or not json_path.is_file():
        return None
    try:
        value = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    return {
        "dataType": dataset["dataType"],
        "releaseDate": dataset["releaseDate"],
        "sourceUrl": dataset["url"],
        "archivePath": archive.name,
        "archiveSha256": _sha256(archive),
        "archiveBytes": archive.stat().st_size,
        "jsonPath": json_path.name,
        "jsonSha256": _sha256(json_path),
        "jsonBytes": json_path.stat().st_size,
    }


def _pin_mismatches(row: dict[str, Any], dataset: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for observed_key, expected_key in _PIN_FIELDS:
        observed = row.get(observed_key)
        expected = dataset.get(expected_key)
        if observed != expected:
            mismatches.append(f"{observed_key} expected={expected!r} observed={observed!r}")
    return mismatches


def _archive_pin_mismatches(path: Path, dataset: dict[str, Any]) -> list[str]:
    if not path.is_file():
        return ["archive missing after download"]
    mismatches: list[str] = []
    observed_sha = _sha256(path)
    observed_bytes = path.stat().st_size
    if observed_sha != dataset["expectedArchiveSha256"]:
        mismatches.append(
            f"archiveSha256 expected={dataset['expectedArchiveSha256']!r} observed={observed_sha!r}"
        )
    if observed_bytes != dataset["expectedArchiveBytes"]:
        mismatches.append(
            f"archiveBytes expected={dataset['expectedArchiveBytes']!r} observed={observed_bytes!r}"
        )
    return mismatches


def _existing_valid(output_dir: Path, dataset: dict[str, Any]) -> dict[str, Any] | None:
    _validate_dataset_definition(dataset)
    row = _observed_dataset(output_dir, dataset)
    if row is None or _pin_mismatches(row, dataset):
        return None
    return row


def _manifest_body(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "kind": REFERENCE_KIND,
        "source": "USDA FoodData Central",
        "policy": {
            "allowedDataTypes": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
            "candidateDiscoveryOnlyUntilReviewed": True,
            "exactFdcBindingRequired": True,
            "searchResultAutoAccepted": False,
            "apiKeyRequired": False,
            "secretsPersisted": False,
            "manifestContentAddressed": True,
            "runtimeTimestampInManifest": False,
            "datasetBytesPinned": True,
            "datasetPinAlgorithm": "SHA-256",
        },
        "datasets": rows,
    }


def _write_manifest(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def prepare(output_dir: Path, *, refresh: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "reference-manifest.v60.json"
    prior_manifest: dict[str, Any] | None = None
    if not refresh and manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loaded = None
        if isinstance(loaded, dict):
            prior_manifest = loaded

    rows: list[dict[str, Any]] = []
    downloaded = 0
    reused = 0

    for dataset in _DATASETS:
        _validate_dataset_definition(dataset)
        existing = None if refresh else _existing_valid(output_dir, dataset)
        if existing is not None:
            rows.append(existing)
            reused += 1
            continue

        archive = output_dir / dataset["archiveName"]
        json_path = output_dir / dataset["jsonName"]
        _download(dataset["url"], archive)
        archive_mismatches = _archive_pin_mismatches(archive, dataset)
        if archive_mismatches:
            raise RuntimeError(
                f"{dataset['dataType']}: downloaded archive differs from pinned USDA bytes: "
                + "; ".join(archive_mismatches)
            )

        _extract_json(archive, json_path, dataset["zipHint"])
        row = _observed_dataset(output_dir, dataset)
        if row is None:
            raise RuntimeError(f"failed to prepare {dataset['dataType']} reference data")
        mismatches = _pin_mismatches(row, dataset)
        if mismatches:
            raise RuntimeError(
                f"{dataset['dataType']}: extracted reference data differs from pinned USDA bytes: "
                + "; ".join(mismatches)
            )
        rows.append(row)
        downloaded += 1

    manifest = _manifest_body(rows)
    manifest_reused = bool(not refresh and prior_manifest == manifest)
    if not manifest_reused:
        # This also migrates earlier timestamped/unpinned v60 manifest formats.
        # Acquisition time belongs in workflow metadata, not the content hash.
        _write_manifest(manifest_path, manifest)

    summary = {
        "datasetCount": len(rows),
        "downloadedDatasetCount": downloaded,
        "reusedDatasetCount": reused,
        "datasetPinsVerified": True,
        "referenceManifestReused": manifest_reused,
        "referenceManifestDeterministic": True,
        "referenceManifestSha256": _sha256(manifest_path),
        "apiKeyRequired": False,
        "secretsPersisted": False,
        "datasets": rows,
        "manifest": str(manifest_path),
    }
    return manifest, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    _manifest, summary = prepare(Path(args.output_dir).expanduser(), refresh=args.refresh)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
