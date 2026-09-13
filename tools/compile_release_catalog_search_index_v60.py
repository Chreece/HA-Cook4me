#!/usr/bin/env python3
"""Attach a precompiled multilingual search index to a Cook4Me release catalog."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
MODULE = COMPONENT / "catalog_search_index.py"


def _load_index_module():
    spec = importlib.util.spec_from_file_location("cook4me_catalog_search_index_build", MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load catalog_search_index.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compile_catalog_file(input_path: Path, output_path: Path) -> dict[str, Any]:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("catalog must be a JSON object")
    if not isinstance(payload.get("recipes"), list):
        raise RuntimeError("catalog recipes must be a list")
    if not isinstance(payload.get("ingredients"), list):
        raise RuntimeError("catalog ingredients must be a list")

    index_module = _load_index_module()
    payload["searchIndex"] = index_module.compile_search_index(payload)
    source = payload.setdefault("source", {})
    if isinstance(source, dict):
        source["compiledMultilingualSearchIndex"] = True
        source["compiledMultilingualSearchIndexSchemaVersion"] = int(
            payload["searchIndex"]["schemaVersion"]
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default=str(COMPONENT / "catalog" / "merged_catalog.v1.json"),
    )
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser() if args.output else input_path
    payload = compile_catalog_file(input_path, output_path)
    search_index = payload["searchIndex"]
    print(
        json.dumps(
            {
                "catalogVersion": payload.get("catalogVersion"),
                "recipes": len(payload.get("recipes") or []),
                "ingredients": len(payload.get("ingredients") or []),
                "searchIndexStats": search_index.get("stats") or {},
                "output": str(output_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
