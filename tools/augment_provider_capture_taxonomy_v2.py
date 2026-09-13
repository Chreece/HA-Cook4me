#!/usr/bin/env python3
"""Overlay taxonomy-only evidence onto a reviewed provider-capture v2.

The output remains a local maintenance artifact. It preserves every provider v2
field and adds only taxonomy fields captured later from the exact same variant
IDs. No provider identity is changed and no taxonomy row is applied to a
non-matching variant.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any
import zipfile

PROVIDER_KIND = "cook4me-provider-capture"
TAXONOMY_KIND = "cook4me-provider-taxonomy-capture-v2"
FIELDS = (
    "courses",
    "occasions",
    "excludedFoods",
    "detectedExcludedFoods",
    "classifications",
    "domain",
)


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load_provider(path: Path) -> dict[str, Any]:
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith("provider-capture-v2.json.gz"):
                    value = json.loads(gzip.decompress(archive.read(name)))
                    break
            else:
                raise RuntimeError("provider-capture-v2.json.gz not found")
    elif path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("kind") != PROVIDER_KIND:
        raise RuntimeError(f"expected {PROVIDER_KIND}")
    return value


def _load_taxonomy(path: Path) -> dict[str, Any]:
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.endswith("provider-taxonomy-v2.json.gz"):
                    value = json.loads(gzip.decompress(archive.read(name)))
                    break
            else:
                raise RuntimeError("provider-taxonomy-v2.json.gz not found")
    else:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    if not isinstance(value, dict) or value.get("kind") != TAXONOMY_KIND:
        raise RuntimeError(f"expected {TAXONOMY_KIND}")
    if not value.get("complete"):
        raise RuntimeError("taxonomy capture is incomplete")
    return value


def augment(provider: dict[str, Any], taxonomy: dict[str, Any]) -> dict[str, Any]:
    by_variant = {
        _text(row.get("variantId")): row
        for row in taxonomy.get("variants") or []
        if isinstance(row, dict) and _text(row.get("variantId"))
    }
    details = provider.get("details") or []
    expected = {
        _text(row.get("variantId"))
        for row in details
        if isinstance(row, dict) and _text(row.get("variantId"))
    }
    missing = sorted(expected - set(by_variant))
    extras = sorted(set(by_variant) - expected)
    if missing:
        raise RuntimeError(f"taxonomy is missing {len(missing)} reviewed provider variants")
    if extras:
        raise RuntimeError(f"taxonomy contains {len(extras)} variants outside reviewed provider capture")

    for detail in details:
        if not isinstance(detail, dict):
            continue
        row = by_variant[_text(detail.get("variantId"))]
        for field in FIELDS:
            if field in row:
                detail[field] = row[field]
    source = provider.setdefault("source", {})
    if isinstance(source, dict):
        source["taxonomyAugmented"] = True
        source["taxonomyVariantCount"] = len(by_variant)
        source["taxonomyFields"] = list(FIELDS)
    return provider


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider-capture", required=True)
    parser.add_argument("--taxonomy", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    provider = _load_provider(Path(args.provider_capture).expanduser())
    taxonomy = _load_taxonomy(Path(args.taxonomy).expanduser())
    payload = augment(provider, taxonomy)
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, "wt", encoding="utf-8", compresslevel=9) as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({"details": len(payload.get("details") or []), "taxonomyAugmented": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
