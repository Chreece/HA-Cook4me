#!/usr/bin/env python3
"""Pinned offline USDA FoodData Central reference support for Cook4Me v60.

The reference corpus is evidence only until a separate reviewed target -> exact
FDC ID binding exists. This module never selects a nutrition identity and never
uses provider search rank as proof.
"""
from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

REFERENCE_KIND = "cook4me-fdc-reference-data-v60"
_ALLOWED_DATA_TYPES = {"Foundation", "SR Legacy"}


def text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm(value: Any) -> str:
    value = unicodedata.normalize("NFKC", text(value)).casefold()
    return re.sub(r"[^0-9a-z]+", " ", value).strip()


def tokens(value: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(part for part in norm(value).split() if part))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _food_rows(payload: Any, data_type: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise RuntimeError(f"{data_type} FDC JSON must be an object")
    preferred = {
        "Foundation": ("FoundationFoods", "foundationFoods"),
        "SR Legacy": ("SRLegacyFoods", "srLegacyFoods"),
    }[data_type]
    for key in (*preferred, "foods"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    lists = [value for value in payload.values() if isinstance(value, list)]
    if len(lists) == 1:
        return [row for row in lists[0] if isinstance(row, dict)]
    raise RuntimeError(f"cannot locate {data_type} food rows in FDC JSON")


def _nested_text(value: Any) -> str:
    if isinstance(value, dict):
        return text(value.get("description") or value.get("name"))
    if isinstance(value, list):
        return "; ".join(filter(None, (_nested_text(item) for item in value)))
    return text(value)


def _candidate_fields(raw: dict[str, Any], data_type: str) -> dict[str, Any] | None:
    try:
        fdc_id = int(raw.get("fdcId"))
    except (TypeError, ValueError):
        return None
    description = text(raw.get("description"))
    if fdc_id <= 0 or not description:
        return None
    row: dict[str, Any] = {
        "fdcId": fdc_id,
        "description": description,
        "dataType": data_type,
    }
    for source, target in (
        ("foodCategory", "foodCategory"),
        ("scientificName", "scientificName"),
        ("commonNames", "commonNames"),
        ("additionalDescriptions", "additionalDescriptions"),
        ("publicationDate", "publicationDate"),
    ):
        value = _nested_text(raw.get(source))
        if value:
            row[target] = value
    return row


class ReferenceIndex:
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path.resolve()
        manifest = _load(self.manifest_path)
        if not isinstance(manifest, dict) or manifest.get("kind") != REFERENCE_KIND:
            raise RuntimeError("invalid FDC reference manifest")
        datasets = manifest.get("datasets") if isinstance(manifest.get("datasets"), list) else []
        if {text(row.get("dataType")) for row in datasets if isinstance(row, dict)} != _ALLOWED_DATA_TYPES:
            raise RuntimeError("FDC reference manifest must contain Foundation and SR Legacy")

        self.manifest = manifest
        self.manifest_sha256 = sha256(self.manifest_path)
        self.records: list[dict[str, Any]] = []
        self._raw_by_id: dict[int, dict[str, Any]] = {}
        self._meta_by_id: dict[int, dict[str, Any]] = {}
        self._token_index: dict[str, set[int]] = defaultdict(set)

        for dataset in datasets:
            if not isinstance(dataset, dict):
                continue
            data_type = text(dataset.get("dataType"))
            if data_type not in _ALLOWED_DATA_TYPES:
                raise RuntimeError(f"unsupported FDC data type: {data_type}")
            rel = text(dataset.get("jsonPath"))
            if not rel:
                raise RuntimeError(f"FDC manifest {data_type} is missing jsonPath")
            path = (self.manifest_path.parent / rel).resolve()
            expected_sha = text(dataset.get("jsonSha256"))
            actual_sha = sha256(path)
            if expected_sha and expected_sha != actual_sha:
                raise RuntimeError(f"FDC reference hash mismatch for {data_type}")
            release_date = text(dataset.get("releaseDate"))
            payload = _load(path)
            for raw in _food_rows(payload, data_type):
                candidate = _candidate_fields(raw, data_type)
                if not candidate:
                    continue
                fdc_id = int(candidate["fdcId"])
                if fdc_id in self._raw_by_id:
                    raise RuntimeError(f"duplicate FDC ID across reference datasets: {fdc_id}")
                raw_copy = dict(raw)
                raw_copy.setdefault("dataType", data_type)
                self._raw_by_id[fdc_id] = raw_copy
                self._meta_by_id[fdc_id] = {
                    "dataType": data_type,
                    "releaseDate": release_date,
                    "jsonSha256": actual_sha,
                }
                record_index = len(self.records)
                self.records.append(candidate)
                searchable = " ".join(
                    text(candidate.get(key))
                    for key in (
                        "description",
                        "foodCategory",
                        "scientificName",
                        "commonNames",
                        "additionalDescriptions",
                    )
                    if candidate.get(key)
                )
                for token in tokens(searchable):
                    self._token_index[token].add(record_index)

    def food(self, fdc_id: int) -> dict[str, Any]:
        try:
            return dict(self._raw_by_id[int(fdc_id)])
        except (KeyError, TypeError, ValueError):
            raise RuntimeError(f"FDC ID {fdc_id} is absent from pinned reference data") from None

    def metadata(self, fdc_id: int) -> dict[str, Any]:
        try:
            return dict(self._meta_by_id[int(fdc_id)])
        except (KeyError, TypeError, ValueError):
            raise RuntimeError(f"FDC ID {fdc_id} is absent from pinned reference data") from None

    @staticmethod
    def _score(query: str, row: dict[str, Any]) -> float:
        q = norm(query)
        d = norm(row.get("description"))
        if not q or not d:
            return 0.0
        q_tokens = set(tokens(q))
        d_tokens = set(tokens(d))
        overlap = len(q_tokens & d_tokens)
        if not overlap:
            extras = norm(
                " ".join(
                    text(row.get(key))
                    for key in ("commonNames", "scientificName", "additionalDescriptions")
                )
            )
            if not (q in extras or any(token in set(tokens(extras)) for token in q_tokens)):
                return 0.0
        coverage = overlap / max(1, len(q_tokens))
        precision = overlap / max(1, len(d_tokens))
        sequence = SequenceMatcher(None, q, d).ratio()
        score = coverage * 400.0 + precision * 80.0 + sequence * 120.0
        if q == d:
            score += 1000.0
        elif d.startswith(q) or q.startswith(d):
            score += 300.0
        elif q in d:
            score += 200.0
        if row.get("dataType") == "Foundation":
            score += 2.0
        return score

    def search(self, query: str, *, max_candidates: int = 8) -> list[dict[str, Any]]:
        query_tokens = tokens(query)
        candidate_indices: set[int] = set()
        for token in query_tokens:
            candidate_indices.update(self._token_index.get(token, set()))
        if not candidate_indices:
            return []
        ranked: list[tuple[float, int, dict[str, Any]]] = []
        for index in candidate_indices:
            row = self.records[index]
            score = self._score(query, row)
            if score <= 0:
                continue
            ranked.append((score, int(row["fdcId"]), row))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        out: list[dict[str, Any]] = []
        for rank, (score, _fdc_id, raw) in enumerate(ranked[: max(1, int(max_candidates))], 1):
            row = dict(raw)
            row["localEvidenceRank"] = rank
            row["localEvidenceScore"] = round(score, 6)
            out.append(row)
        return out
