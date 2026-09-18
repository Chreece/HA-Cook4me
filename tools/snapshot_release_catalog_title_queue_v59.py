#!/usr/bin/env python3
"""Snapshot unresolved Cook4Me recipe-title review tasks into deterministic batches.

This maintenance helper consumes an already-reviewed local translation queue. It
never crawls the provider, mutates provider identities, translates labels, or
stores credentials. It only projects unresolved ``recipe_title_english`` tasks
into a stable review snapshot plus per-language batches.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import shutil
from typing import Any


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def title_tasks(queue: dict[str, Any]) -> list[dict[str, Any]]:
    if queue.get("kind") != "cook4me-local-translation-queue":
        raise RuntimeError("expected cook4me-local-translation-queue")
    rows = [
        dict(row)
        for row in queue.get("tasks") or []
        if isinstance(row, dict) and row.get("type") == "recipe_title_english"
    ]
    for row in rows:
        if not _text(row.get("taskId")):
            raise RuntimeError("recipe-title task is missing taskId")
        if not _text(row.get("sourceLanguage")):
            raise RuntimeError(f"recipe-title task {_text(row.get('taskId'))} is missing sourceLanguage")
        if not _text(row.get("sourceText")):
            raise RuntimeError(f"recipe-title task {_text(row.get('taskId'))} is missing sourceText")
    rows.sort(
        key=lambda row: (
            _text(row.get("sourceLanguage")).lower(),
            _text(row.get("sourceText")).casefold(),
            _text(row.get("taskId")),
        )
    )
    task_ids = [_text(row.get("taskId")) for row in rows]
    if len(task_ids) != len(set(task_ids)):
        raise RuntimeError("recipe-title queue contains duplicate task IDs")
    return rows


def snapshot(
    queue: dict[str, Any], *, source_queue: str, batch_size: int
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    tasks = title_tasks(queue)
    counts = Counter(_text(row.get("sourceLanguage")).lower() for row in tasks)
    generated_at = _text(queue.get("generatedAt"))
    payload = {
        "schema": 1,
        "kind": "cook4me-release-catalog-pending-recipe-title-review-v59",
        "generatedAt": generated_at,
        "sourceQueue": source_queue,
        "providerIdentityUnchanged": True,
        "recipeTitleTasksRemaining": len(tasks),
        "remainingByLanguage": dict(sorted(counts.items())),
        "tasks": tasks,
    }
    summary = {
        "generatedAt": generated_at,
        "sourceQueue": source_queue,
        "recipeTitleTasksRemaining": len(tasks),
        "remainingByLanguage": payload["remainingByLanguage"],
        "batchSize": batch_size,
    }

    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in tasks:
        by_language[_text(row.get("sourceLanguage")).lower()].append(row)
    batches: dict[str, dict[str, Any]] = {}
    for language in sorted(by_language):
        rows = by_language[language]
        for offset in range(0, len(rows), batch_size):
            part = offset // batch_size + 1
            name = f"{language}_{part:02d}.json"
            chunk = rows[offset : offset + batch_size]
            batches[name] = {
                "schema": 1,
                "kind": "cook4me-release-catalog-pending-recipe-title-batch-v59",
                "generatedAt": generated_at,
                "sourceQueue": source_queue,
                "language": language,
                "part": part,
                "taskCount": len(chunk),
                "tasks": chunk,
            }
    summary["batchCount"] = len(batches)
    return payload, summary, batches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--batch-dir", required=True)
    parser.add_argument("--batch-size", type=int, default=50)
    args = parser.parse_args()

    queue_path = Path(args.queue).expanduser()
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    if not isinstance(queue, dict):
        raise RuntimeError("translation queue must be a JSON object")
    payload, summary, batches = snapshot(
        queue, source_queue=str(queue_path), batch_size=args.batch_size
    )

    output = Path(args.output).expanduser()
    summary_path = Path(args.summary).expanduser()
    batch_dir = Path(args.batch_dir).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    if batch_dir.exists():
        shutil.rmtree(batch_dir)
    batch_dir.mkdir(parents=True, exist_ok=True)

    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, batch in batches.items():
        (batch_dir / name).write_text(
            json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
