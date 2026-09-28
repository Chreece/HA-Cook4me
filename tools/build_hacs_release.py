#!/usr/bin/env python3
"""Build the compact HACS zip-release payload.

The repository keeps the merged catalog as JSON for development/audits. The HACS
asset stores that catalog as gzip and omits retired compiled frontend bundles so
HACS backs up/extracts/copies a much smaller integration directory.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "cook4me"
PREFIX = "custom_components/cook4me/"
RAW_CATALOG = "catalog/merged_catalog.v1.json"
GZ_CATALOG = RAW_CATALOG + ".gz"
RETIRED_BUNDLE = re.compile(r"frontend/cook4me-panel-v(\d+)-bundle\.js$")


def tracked_runtime_files() -> list[str]:
    output = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files", "-z", PREFIX]
    ).decode()
    return [
        path[len(PREFIX):]
        for path in output.split("\0")
        if path and path.startswith(PREFIX)
    ]


def retired(path: str) -> bool:
    match = RETIRED_BUNDLE.fullmatch(path)
    return bool(match and int(match.group(1)) < 126)


def manifest_bytes(version: str | None) -> bytes:
    data = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    if version:
        data["version"] = version
    return (json.dumps(data, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def gzip_catalog() -> tuple[bytes, bytes]:
    raw = (INTEGRATION / RAW_CATALOG).read_bytes()
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    return raw, compressed


def add_bytes(archive: ZipFile, name: str, data: bytes, *, stored: bool = False) -> None:
    info = ZipInfo(name)
    # Reproducible timestamp accepted by the ZIP format.
    info.date_time = (1980, 1, 1, 0, 0, 0)
    info.external_attr = 0o100644 << 16
    info.compress_type = ZIP_STORED if stored else ZIP_DEFLATED
    archive.writestr(info, data)


def build(output: Path, *, version: str | None = None) -> dict:
    files = tracked_runtime_files()
    raw_catalog, compressed_catalog = gzip_catalog()
    output.parent.mkdir(parents=True, exist_ok=True)

    included: list[str] = []
    source_runtime_bytes = 0
    packaged_runtime_bytes = 0

    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in files:
            source = INTEGRATION / relative
            if not source.is_file():
                continue
            source_runtime_bytes += source.stat().st_size
            if relative == RAW_CATALOG or retired(relative):
                continue
            data = manifest_bytes(version) if relative == "manifest.json" else source.read_bytes()
            add_bytes(archive, relative, data)
            included.append(relative)
            packaged_runtime_bytes += len(data)

        add_bytes(archive, GZ_CATALOG, compressed_catalog, stored=True)
        included.append(GZ_CATALOG)
        packaged_runtime_bytes += len(compressed_catalog)

    report = {
        "output": str(output),
        "version": version or json.loads((INTEGRATION / "manifest.json").read_text())["version"],
        "files": len(included),
        "zipBytes": output.stat().st_size,
        "sourceRuntimeBytes": source_runtime_bytes,
        "packagedRuntimeBytes": packaged_runtime_bytes,
        "rawCatalogBytes": len(raw_catalog),
        "compressedCatalogBytes": len(compressed_catalog),
        "catalogCompressionPercent": round(100 * (1 - len(compressed_catalog) / len(raw_catalog)), 2),
        "installedPayloadReductionPercent": round(
            100 * (1 - packaged_runtime_bytes / source_runtime_bytes), 2
        ),
        "catalogSha256": hashlib.sha256(raw_catalog).hexdigest(),
        "compressedCatalogSha256": hashlib.sha256(compressed_catalog).hexdigest(),
        "rawCatalogIncluded": RAW_CATALOG in included,
        "compressedCatalogIncluded": GZ_CATALOG in included,
        "retiredBundlesIncluded": sum(retired(path) for path in included),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "cook4me.zip")
    parser.add_argument("--version")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = build(args.output, version=args.version)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
