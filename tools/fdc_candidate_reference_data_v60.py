#!/usr/bin/env python3
"""Lightweight candidate-only USDA FDC index for post-activation review evidence.

The normal :class:`fdc_reference_data_v60.ReferenceIndex` intentionally retains a
full raw copy of every USDA food record because exact reviewed-FDC resolution
later needs nutrient details. Bulk candidate discovery needs only compact
candidate metadata and the lexical token index. Keeping the full raw Foundation,
SR Legacy and FNDDS records in memory during a 1,000+ target evidence pass wastes
hundreds of MB and can force hosted runners into heavy memory pressure.

Candidate scoring is byte-compatible with ``ReferenceIndex`` but stores private
precomputed normalization/token metadata beside each compact candidate. That
avoids repeating Unicode normalization, regex tokenization, and lexical-form
expansion for the same USDA row on every target search. Private score metadata is
never added to candidate rows, so it cannot leak into immutable evidence JSON.

This index cannot resolve nutrition profiles: ``food()`` and ``metadata()`` fail
closed.
"""
from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import fdc_reference_data_v60 as reference


_ScoreRow = tuple[str, frozenset[str], frozenset[str], str, frozenset[str]]


class CandidateReferenceIndex(reference.ReferenceIndex):
    """Search-compatible FDC index that deliberately retains no raw food rows."""

    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path.resolve()
        manifest = reference._load(self.manifest_path)
        if not isinstance(manifest, dict) or manifest.get("kind") != reference.REFERENCE_KIND:
            raise RuntimeError("invalid FDC reference manifest")
        datasets = manifest.get("datasets") if isinstance(manifest.get("datasets"), list) else []
        present_types = {
            reference.text(row.get("dataType"))
            for row in datasets
            if isinstance(row, dict)
        }
        if present_types != reference._ALLOWED_DATA_TYPES:
            raise RuntimeError(
                "FDC reference manifest must contain Foundation, SR Legacy, and Survey (FNDDS)"
            )

        self.manifest = manifest
        self.manifest_sha256 = reference.sha256(self.manifest_path)
        self.records: list[dict[str, Any]] = []
        self._score_rows: list[_ScoreRow] = []
        self._token_index: dict[str, set[int]] = defaultdict(set)
        seen_fdc_ids: set[int] = set()
        self.candidate_only = True

        for dataset in datasets:
            if not isinstance(dataset, dict):
                continue
            data_type = reference.text(dataset.get("dataType"))
            if data_type not in reference._ALLOWED_DATA_TYPES:
                raise RuntimeError(f"unsupported FDC data type: {data_type}")
            rel = reference.text(dataset.get("jsonPath"))
            if not rel:
                raise RuntimeError(f"FDC manifest {data_type} is missing jsonPath")
            path = (self.manifest_path.parent / rel).resolve()
            expected_sha = reference.text(dataset.get("jsonSha256"))
            actual_sha = reference.sha256(path)
            if expected_sha and expected_sha != actual_sha:
                raise RuntimeError(f"FDC reference hash mismatch for {data_type}")

            payload = reference._load(path)
            for raw in reference._food_rows(payload, data_type):
                candidate = reference._candidate_fields(raw, data_type)
                if not candidate:
                    continue
                fdc_id = int(candidate["fdcId"])
                if fdc_id in seen_fdc_ids:
                    raise RuntimeError(f"duplicate FDC ID across reference datasets: {fdc_id}")
                seen_fdc_ids.add(fdc_id)

                record_index = len(self.records)
                self.records.append(candidate)

                description = reference.norm(candidate.get("description"))
                description_raw_tokens = frozenset(reference.tokens(description))
                description_tokens = frozenset(reference.lexical_tokens(description))
                extras = reference.norm(
                    " ".join(
                        reference.text(candidate.get(key))
                        for key in (
                            "commonNames",
                            "scientificName",
                            "additionalDescriptions",
                        )
                        if candidate.get(key)
                    )
                )
                extra_tokens = frozenset(reference.lexical_tokens(extras))
                self._score_rows.append(
                    (
                        description,
                        description_raw_tokens,
                        description_tokens,
                        extras,
                        extra_tokens,
                    )
                )

                searchable = " ".join(
                    reference.text(candidate.get(key))
                    for key in (
                        "description",
                        "foodCategory",
                        "scientificName",
                        "commonNames",
                        "additionalDescriptions",
                    )
                    if candidate.get(key)
                )
                for token in reference.lexical_tokens(searchable):
                    self._token_index[token].add(record_index)

            del payload

        if len(self._score_rows) != len(self.records):
            raise RuntimeError("candidate score metadata/index length mismatch")
        self.indexed_fdc_id_count = len(seen_fdc_ids)

    def _rank(
        self, query: str, *, max_candidates: int
    ) -> list[tuple[float, int, dict[str, Any]]]:
        """Rank with the exact ReferenceIndex formula using cached row metadata."""
        query_lookup_tokens = reference.lexical_tokens(query)
        candidate_indices: set[int] = set()
        for token in query_lookup_tokens:
            candidate_indices.update(self._token_index.get(token, set()))
        if not candidate_indices:
            return []

        q = reference.norm(query)
        if not q:
            return []
        q_raw_tokens = frozenset(reference.tokens(q))
        q_tokens = frozenset(reference.lexical_tokens(q))

        ranked: list[tuple[float, int, dict[str, Any]]] = []
        for index in candidate_indices:
            row = self.records[index]
            d, d_raw_tokens, d_tokens, extras, extra_tokens = self._score_rows[index]
            if not d:
                continue
            overlap = len(q_tokens & d_tokens)
            if not overlap:
                if not (q in extras or q_tokens.intersection(extra_tokens)):
                    continue
            coverage = overlap / max(1, len(q_tokens))
            precision = overlap / max(1, len(d_tokens))
            sequence = SequenceMatcher(None, q, d).ratio()
            score = coverage * 400.0 + precision * 80.0 + sequence * 120.0
            if q == d:
                score += 1000.0
            elif q_raw_tokens and q_raw_tokens == d_raw_tokens:
                score += 900.0
            elif d.startswith(q) or q.startswith(d):
                score += 300.0
            elif q in d:
                score += 200.0
            if row.get("dataType") == "Foundation":
                score += 2.0
            if score <= 0:
                continue
            ranked.append((score, int(row["fdcId"]), row))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked[: max(1, int(max_candidates))]

    def food(self, fdc_id: int) -> dict[str, Any]:
        raise RuntimeError(
            "CandidateReferenceIndex is evidence-only and cannot return raw FDC food records"
        )

    def metadata(self, fdc_id: int) -> dict[str, Any]:
        raise RuntimeError(
            "CandidateReferenceIndex is evidence-only and cannot provide resolution metadata"
        )
