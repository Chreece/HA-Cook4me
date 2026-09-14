#!/usr/bin/env python3
"""Resolve Cook4Me release-catalog canonical labels using local Ollama only.

The input queue contains public provider recipe titles/ingredient labels only.
No account credentials or provider secrets are sent to Ollama, no cloud fallback
exists, and successful task results are cached in SQLite for interruption-safe
resume.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any
import urllib.request

SCHEMA_VERSION = 1
PROMPT_VERSION = "cook4me-local-canonical-v1"
CLASSIFICATIONS = {"food", "equipment", "other", "ambiguous"}
EMBED_TOKENS = ("embed", "embedding", "nomic", "bge", "mxbai", "snowflake", "e5-")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _task_hash(task: dict[str, Any]) -> str:
    return hashlib.sha256(
        (PROMPT_VERSION + "\0" + _canonical(task)).encode("utf-8")
    ).hexdigest()


def _http_json(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    data = None
    headers = {"User-Agent": "HA-Cook4me-local-translation/1"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("Ollama returned a non-object response")
    return value


def _size_bytes(model: dict[str, Any]) -> int:
    try:
        return int(model.get("size") or 0)
    except (TypeError, ValueError):
        return 0


def _parameter_billions(model: dict[str, Any]) -> float:
    text = str(
        (model.get("details") or {}).get("parameter_size")
        or model.get("name")
        or model.get("model")
        or ""
    )
    match = re.search(r"(\d+(?:\.\d+)?)\s*[bB]", text)
    return float(match.group(1)) if match else 0.0


def select_model(models: list[Any]) -> str:
    """Pick the largest installed non-embedding model with a conservative size."""
    usable: list[dict[str, Any]] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        name = str(model.get("name") or model.get("model") or "")
        if not name or any(token in name.casefold() for token in EMBED_TOKENS):
            continue
        usable.append(model)
    if not usable:
        raise RuntimeError("No non-embedding Ollama model is installed")

    # Leave headroom for Ollama/runtime plus the other GPU workloads. Maintainers
    # can always override this automatic choice with COOK4ME_OLLAMA_MODEL.
    safe = [
        model
        for model in usable
        if 0 < _size_bytes(model) <= 16 * 1024**3
    ]
    pool = safe or usable
    pool.sort(
        key=lambda model: (
            _parameter_billions(model),
            _size_bytes(model),
            str(model.get("name") or model.get("model") or ""),
        ),
        reverse=True,
    )
    return str(pool[0].get("name") or pool[0].get("model"))


def discover_model(base_url: str, explicit: str = "") -> str:
    if explicit:
        return explicit
    payload = _http_json(base_url.rstrip("/") + "/api/tags", timeout=15)
    return select_model(payload.get("models") or [])


def _system_prompt() -> str:
    return """You canonicalize public Cook4Me catalog labels locally. Return JSON only. Never infer or merge provider recipe identities.
Rules:
- canonicalEnglish must be concise, faithful English, preserving specificity and proper nouns.
- provider_food_english: derive one ingredient name from the multilingual evidence labels. It is a food.
- recipe_title_english: translate the title only; do not deduplicate or reinterpret it.
- unkeyed_ingredient: classify as exactly food, equipment, other, or ambiguous. Translate if needed. A compound food label may remain compound. Use ambiguous when the text is too unclear to classify safely.
- No explanations and no markdown.
Return exactly {\"results\":[{\"taskId\":\"...\",\"canonicalEnglish\":\"...\",\"classification\":\"...\"}]} in the same task order. classification is required only for unkeyed_ingredient."""


def _prompt_tasks(tasks: list[dict[str, Any]]) -> str:
    rows: list[dict[str, Any]] = []
    for task in tasks:
        if task["type"] == "provider_food_english":
            rows.append(
                {
                    "taskId": task["taskId"],
                    "type": task["type"],
                    "providerFoodKey": task["providerFoodKey"],
                    "evidenceLabels": task.get("evidenceLabels") or [],
                }
            )
        else:
            rows.append(
                {
                    "taskId": task["taskId"],
                    "type": task["type"],
                    "sourceLanguage": task.get("sourceLanguage"),
                    "sourceText": task.get("sourceText"),
                    "needsTranslation": task.get("needsTranslation", True),
                }
            )
    return "Input tasks:\n" + _canonical(rows)


def _parse_model_json(text: Any) -> dict[str, Any]:
    value = str(text or "").strip()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        end = value.rfind("}")
        if start < 0 or end <= start:
            raise
        payload = json.loads(value[start : end + 1])
    if not isinstance(payload, dict):
        raise ValueError("model result is not an object")
    return payload


def validate_batch(
    tasks: list[dict[str, Any]], payload: dict[str, Any]
) -> list[dict[str, str]]:
    rows = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or len(rows) != len(tasks):
        raise ValueError("result count mismatch")

    output: list[dict[str, str]] = []
    for task, row in zip(tasks, rows):
        if not isinstance(row, dict) or row.get("taskId") != task["taskId"]:
            raise ValueError("task ID/order mismatch")
        english = re.sub(
            r"\s+", " ", str(row.get("canonicalEnglish") or "").strip()
        )
        if not english or len(english) > 240:
            raise ValueError(f"{task['taskId']}: invalid canonicalEnglish")
        result = {
            "taskId": task["taskId"],
            "canonicalEnglish": english,
        }
        if task["type"] == "unkeyed_ingredient":
            classification = str(row.get("classification") or "").strip().casefold()
            if classification not in CLASSIFICATIONS:
                raise ValueError(
                    f"{task['taskId']}: invalid classification"
                )
            result["classification"] = classification
        output.append(result)
    return output


def generate_batch(
    base_url: str,
    model: str,
    tasks: list[dict[str, Any]],
) -> list[dict[str, str]]:
    payload = _http_json(
        base_url.rstrip("/") + "/api/generate",
        method="POST",
        body={
            "model": model,
            "system": _system_prompt(),
            "prompt": _prompt_tasks(tasks),
            "format": "json",
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=240,
    )
    return validate_batch(tasks, _parse_model_json(payload.get("response")))


def _open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS translations (
            task_id TEXT PRIMARY KEY,
            input_hash TEXT NOT NULL,
            model TEXT NOT NULL,
            schema_version INTEGER NOT NULL,
            result_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    return connection


def _cached(
    connection: sqlite3.Connection,
    task: dict[str, Any],
    model: str,
) -> dict[str, str] | None:
    row = connection.execute(
        "SELECT result_json,input_hash,model,schema_version "
        "FROM translations WHERE task_id=?",
        (task["taskId"],),
    ).fetchone()
    if (
        not row
        or row[1] != _task_hash(task)
        or row[2] != model
        or int(row[3]) != SCHEMA_VERSION
    ):
        return None
    try:
        result = json.loads(row[0])
        return validate_batch([task], {"results": [result]})[0]
    except Exception:
        return None


def _store(
    connection: sqlite3.Connection,
    task: dict[str, Any],
    model: str,
    result: dict[str, str],
) -> None:
    with connection:
        connection.execute(
            "INSERT INTO translations(task_id,input_hash,model,schema_version,result_json,updated_at) "
            "VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(task_id) DO UPDATE SET "
            "input_hash=excluded.input_hash,model=excluded.model,schema_version=excluded.schema_version," 
            "result_json=excluded.result_json,updated_at=excluded.updated_at",
            (
                task["taskId"],
                _task_hash(task),
                model,
                SCHEMA_VERSION,
                _canonical(result),
                _iso_now(),
            ),
        )


def _translate_resilient(
    base_url: str,
    model: str,
    tasks: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Split only malformed model output; transport/model failures stay fatal."""
    try:
        return generate_batch(base_url, model, tasks), []
    except (ValueError, json.JSONDecodeError) as exc:
        if len(tasks) == 1:
            return [], [
                {
                    "taskId": tasks[0]["taskId"],
                    "error": type(exc).__name__ + ": " + str(exc),
                }
            ]
        midpoint = len(tasks) // 2
        left, left_failures = _translate_resilient(
            base_url, model, tasks[:midpoint]
        )
        right, right_failures = _translate_resilient(
            base_url, model, tasks[midpoint:]
        )
        return left + right, left_failures + right_failures


def _load_queue(path: Path) -> dict[str, Any]:
    queue = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(queue, dict)
        or queue.get("kind") != "cook4me-local-translation-queue"
        or int(queue.get("schemaVersion") or 0) != 2
    ):
        raise RuntimeError("translation queue is not assembly schema v2")
    tasks = queue.get("tasks") or []
    ids = [task.get("taskId") for task in tasks]
    if len(ids) != len(set(ids)):
        raise RuntimeError("translation queue contains duplicate task IDs")
    return queue


def run(args: argparse.Namespace) -> dict[str, Any]:
    queue = _load_queue(Path(args.queue).expanduser())
    tasks = list(queue["tasks"])
    if args.limit:
        tasks = tasks[: max(1, int(args.limit))]

    base_url = args.ollama_url.rstrip("/")
    model = discover_model(base_url, args.model)
    connection = _open_db(Path(args.cache_db).expanduser())
    try:
        results: dict[str, dict[str, str]] = {}
        pending: list[dict[str, Any]] = []
        for task in tasks:
            hit = _cached(connection, task, model)
            if hit is None:
                pending.append(task)
            else:
                results[task["taskId"]] = hit

        print(f"OLLAMA_MODEL={model}", flush=True)
        print(
            f"TASKS={len(tasks)} CACHED={len(results)} PENDING={len(pending)}",
            flush=True,
        )

        failures: list[dict[str, str]] = []
        completed_pending = 0
        batch_size = max(1, min(int(args.batch_size), 32))
        for start in range(0, len(pending), batch_size):
            batch = pending[start : start + batch_size]
            translated, batch_failures = _translate_resilient(
                base_url, model, batch
            )
            translated_by_id = {
                result["taskId"]: result for result in translated
            }
            for task in batch:
                result = translated_by_id.get(task["taskId"])
                if result is not None:
                    _store(connection, task, model, result)
                    results[task["taskId"]] = result
            failures.extend(batch_failures)
            completed_pending += len(batch)
            if (
                completed_pending % 256 < batch_size
                or completed_pending == len(pending)
            ):
                print(
                    f"TRANSLATED={completed_pending}/{len(pending)}",
                    flush=True,
                )

        ordered = [
            results[task["taskId"]]
            for task in tasks
            if task["taskId"] in results
        ]
        output = {
            "schemaVersion": 1,
            "kind": "cook4me-local-translation-results",
            "generatedAt": _iso_now(),
            "localOnly": True,
            "cloudFallback": False,
            "model": model,
            "promptVersion": PROMPT_VERSION,
            "queueGeneratedAt": queue.get("generatedAt"),
            "queueTaskCount": len(tasks),
            "completed": len(ordered),
            "failed": len(failures),
            "results": ordered,
            "failures": failures,
        }
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(
            output_path, "wt", encoding="utf-8", compresslevel=9
        ) as handle:
            json.dump(
                output,
                handle,
                ensure_ascii=False,
                separators=(",", ":"),
            )

        summary = {
            "model": model,
            "tasks": len(tasks),
            "completed": len(ordered),
            "failed": len(failures),
            "cachedAtStart": len(tasks) - len(pending),
            "pendingAtStart": len(pending),
        }
        Path(args.summary).expanduser().write_text(
            json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if args.failures:
            Path(args.failures).expanduser().write_text(
                json.dumps(failures, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        return summary
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", required=True)
    parser.add_argument("--cache-db", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--failures", default="")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="")
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    summary = run(args)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if not summary["failed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
