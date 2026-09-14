#!/usr/bin/env python3
"""Snapshot unresolved keyless ingredient semantics into deterministic review batches."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unicodedata
from typing import Any


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", _text(value)).casefold()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def snapshot(
    queue: dict[str, Any],
    *,
    batch_size: int = 100,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    if queue.get("kind") != "cook4me-local-translation-queue":
        raise RuntimeError("expected cook4me-local-translation-queue")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    tasks = [
        dict(row)
        for row in queue.get("tasks") or []
        if isinstance(row, dict) and row.get("type") == "unkeyed_ingredient"
    ]
    for row in tasks:
        row["sourceLanguage"] = _text(row.get("sourceLanguage")).lower()
        row["sourceText"] = _text(row.get("sourceText"))
        row["taskId"] = _text(row.get("taskId"))
        try:
            row["occurrenceCount"] = max(0, int(row.get("occurrenceCount") or 0))
        except (TypeError, ValueError):
            row["occurrenceCount"] = 0

    tasks.sort(
        key=lambda row: (
            -int(row["occurrenceCount"]),
            row["sourceLanguage"],
            _norm(row["sourceText"]),
            row["taskId"],
        )
    )

    by_language = Counter(row["sourceLanguage"] for row in tasks)
    by_language_occurrences: Counter[str] = Counter()
    translation_needed = 0
    provider_structured_food = 0
    for row in tasks:
        by_language_occurrences[row["sourceLanguage"]] += int(row["occurrenceCount"])
        if bool(row.get("needsTranslation")):
            translation_needed += 1
        requested = row.get("requestedClassification")
        if requested == ["food"]:
            provider_structured_food += 1

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(tasks), batch_size):
        chunk = tasks[offset : offset + batch_size]
        batches.append(
            {
                "schemaVersion": 1,
                "kind": "cook4me-keyless-ingredient-review-source-batch-v59",
                "phase": 3,
                "part": offset // batch_size + 1,
                "batchSize": len(chunk),
                "rankStart": offset + 1,
                "rankEnd": offset + len(chunk),
                "sort": "occurrenceCount-desc,language,sourceText,taskId",
                "tasks": chunk,
            }
        )

    generated_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "schemaVersion": 1,
        "kind": "cook4me-release-catalog-pending-keyless-review-v59",
        "generatedAt": generated_at,
        "sourceQueueSchemaVersion": queue.get("schemaVersion"),
        "taskCount": len(tasks),
        "occurrenceCount": sum(int(row["occurrenceCount"]) for row in tasks),
        "batchSize": batch_size,
        "batchCount": len(batches),
        "sort": "occurrenceCount-desc,language,sourceText,taskId",
        "tasks": tasks,
    }
    summary = {
        "generatedAt": generated_at,
        "taskCount": len(tasks),
        "occurrenceCount": payload["occurrenceCount"],
        "batchCount": len(batches),
        "translationNeeded": translation_needed,
        "providerStructuredFoodClassification": provider_structured_food,
        "remainingByLanguage": dict(sorted(by_language.items())),
        "remainingOccurrencesByLanguage": dict(sorted(by_language_occurrences.items())),
    }
    return payload, summary, batches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--batch-dir", required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    queue = _load(Path(args.queue).expanduser())
    payload, summary, batches = snapshot(queue, batch_size=args.batch_size)

    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_path = Path(args.summary).expanduser()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    batch_dir = Path(args.batch_dir).expanduser()
    batch_dir.mkdir(parents=True, exist_ok=True)
    for old in batch_dir.glob("release_catalog_pending_keyless_phase3_*_source_v59.json"):
        old.unlink()
    for batch in batches:
        part = int(batch["part"])
        path = batch_dir / f"release_catalog_pending_keyless_phase3_{part:03d}_source_v59.json"
        path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
