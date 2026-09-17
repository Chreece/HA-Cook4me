#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PARENT = "48491e67f126366d773d6ab5d39695e5dd286b3a"
BATCH6 = "acead46870d2ad0f2e38fbf78ad42abfb471f801"
CONFIRM = TOOLS / "release_catalog_semantic_confirmations.v1.json"
STANDALONE = TOOLS / "release_catalog_semantic_standalone_dispositions.v1.json"

UNSAFE_IDS = {
    "local:uk:03b0818b595c5d09761c",  # finely chopped bacon -> chopped bacon
    "local:uk:953617d433fc7f71ea28",  # scraped/peeled vanilla pod -> scraped vanilla pod
    "local:uk:97553c4a23b39c4f285d",  # fresh parsley -> generic parsley
    "local:uk:eef3cdfcd9a6230db7e6",  # rosemary sprigs -> generic rosemary
}
SAFE_IDS = {
    "local:bg:e35ac76229b5c78378c4",
    "local:ja:02e1cc34d04a7bdf1a2f",
    "local:pl:9ef3a75831f2a1e3d8bf",
    "local:uk:20cb4d6ecfe7f387415e",
    "local:uk:37af35ccce43b7044807",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _show(commit: str, path: str) -> dict[str, Any]:
    raw = subprocess.check_output(["git", "show", f"{commit}:{path}"], text=True)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise RuntimeError(f"{commit}:{path}: expected JSON object")
    return value


def _by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("sourceIngredientId")): row
        for row in payload.get("items") or []
        if isinstance(row, dict) and row.get("sourceIngredientId")
    }


def _write(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> int:
    parent_confirm = _by_id(_show(PARENT, "tools/release_catalog_semantic_confirmations.v1.json"))
    batch6_confirm = _by_id(_show(BATCH6, "tools/release_catalog_semantic_confirmations.v1.json"))
    parent_standalone = _by_id(_show(PARENT, "tools/release_catalog_semantic_standalone_dispositions.v1.json"))
    batch6_standalone = _by_id(_show(BATCH6, "tools/release_catalog_semantic_standalone_dispositions.v1.json"))
    batch6_ids = set(batch6_confirm) - set(parent_confirm)
    removed_ids = set(parent_standalone) - set(batch6_standalone)
    if batch6_ids != removed_ids or batch6_ids != (SAFE_IDS | UNSAFE_IDS):
        raise RuntimeError(
            f"batch6 historical decision set drift: confirmations={sorted(batch6_ids)} standalone={sorted(removed_ids)}"
        )

    confirmations = _load(CONFIRM)
    current_confirm = _by_id(confirmations)
    missing = (SAFE_IDS | UNSAFE_IDS) - set(current_confirm)
    if missing:
        raise RuntimeError(f"batch6 confirmations missing from current ledger: {sorted(missing)}")
    confirmations["items"] = [
        row for row in confirmations.get("items") or []
        if isinstance(row, dict) and row.get("sourceIngredientId") not in UNSAFE_IDS
    ]

    standalone = _load(STANDALONE)
    current_standalone = _by_id(standalone)
    overlap = UNSAFE_IDS & set(current_standalone)
    if overlap:
        raise RuntimeError(f"unsafe batch6 rows are already standalone: {sorted(overlap)}")
    for source_id in sorted(UNSAFE_IDS):
        standalone.setdefault("items", []).append(parent_standalone[source_id])
    standalone["items"] = sorted(
        [row for row in standalone.get("items") or [] if isinstance(row, dict)],
        key=lambda row: str(row.get("sourceIngredientId") or ""),
    )
    ambiguous = sum(
        row.get("disposition") == "reviewed-ambiguous-source-fragment"
        for row in standalone["items"]
    )
    standalone["summary"] = {
        "standaloneDispositionCount": len(standalone["items"]),
        "reviewedAmbiguousCount": ambiguous,
        "reviewedSourceLocalStandaloneCount": len(standalone["items"]) - ambiguous,
    }

    _write(CONFIRM, confirmations)
    _write(STANDALONE, standalone)
    print(json.dumps({
        "restoredUnsafe": sorted(UNSAFE_IDS),
        "keptSafe": sorted(SAFE_IDS),
        "standaloneAfter": standalone["summary"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
