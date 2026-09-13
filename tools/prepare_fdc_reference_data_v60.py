#!/usr/bin/env python3
"""Download and pin the USDA FDC reference datasets used by v60 review.

This downloads public USDA archives only. It needs no FDC/data.gov API key and
persists no credential. The pinned releases are Foundation Foods April 2026,
final SR Legacy April 2018, and FNDDS 2021-2023 published October 2024.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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

_DATASETS = (
    {
        "dataType": "Foundation",
        "releaseDate": "2026-04-30",
        "url": FOUNDATION_URL,
        "archiveName": "foundation-2026-04-30.zip",
        "jsonName": "foundation-2026-04-30.json",
        "zipHint": "foundation",
    },
    {
        "dataType": "SR Legacy",
        "releaseDate": "2018-04",
        "url": SR_LEGACY_URL,
        "archiveName": "sr-legacy-2018-04.zip",
        "jsonName": "sr-legacy-2018-04.json",
        "zipHint": "sr_legacy",
    },
    {
        "dataType": "Survey (FNDDS)",
        "releaseDate": "2024-10-31",
        "url": FNDDS_URL,
        "archiveName": "fndds-2021-2023-2024-10-31.zip",
        "jsonName": "fndds-2021-2023-2024-10-31.json",
        "zipHint": "survey",
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
            # Prove it is parseable before accepting the extracted bytes.
            value = json.loads(temporary.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise RuntimeError(f"{archive}: extracted FDC JSON is not an object")
            temporary.replace(output)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _existing_valid(output_dir: Path, dataset: dict[str, str]) -> dict[str, Any] | None:
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


def _manifest_without_generated_at(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or value.get("kind") != REFERENCE_KIND:
        return None
    return {key: child for key, child in value.items() if key != "generatedAt"}


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
        },
        "datasets": rows,
    }


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
        existing = None if refresh else _existing_valid(output_dir, dataset)
        if existing is not None:
            rows.append(existing)
            reused += 1
            continue
        archive = output_dir / dataset["archiveName"]
        json_path = output_dir / dataset["jsonName"]
        _download(dataset["url"], archive)
        _extract_json(archive, json_path, dataset["zipHint"])
        row = _existing_valid(output_dir, dataset)
        if row is None:
            raise RuntimeError(f"failed to prepare {dataset['dataType']} reference data")
        rows.append(row)
        downloaded += 1

    body = _manifest_body(rows)
    manifest_reused = bool(
        not refresh
        and prior_manifest is not None
        and _manifest_without_generated_at(prior_manifest) == body
        and isinstance(prior_manifest.get("generatedAt"), str)
        and prior_manifest.get("generatedAt")
    )
    if manifest_reused:
        # Leave the existing file byte-for-byte untouched. This preserves the
        # evidence SHA whenever the pinned USDA archives/JSON are unchanged.
        manifest = prior_manifest
    else:
        manifest = {
            "schemaVersion": 1,
            "kind": REFERENCE_KIND,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "source": body["source"],
            "policy": body["policy"],
            "datasets": rows,
        }
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    summary = {
        "datasetCount": len(rows),
        "downloadedDatasetCount": downloaded,
        "reusedDatasetCount": reused,
        "referenceManifestReused": manifest_reused,
        "referenceManifestSha256": _sha256(manifest_path),
        "apiKeyRequired": False,
        "secretsPersisted": False,
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
