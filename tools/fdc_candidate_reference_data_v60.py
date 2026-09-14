#!/usr/bin/env python3
"""Lightweight candidate-only USDA FDC index for post-activation review evidence.

The normal :class:`fdc_reference_data_v60.ReferenceIndex` intentionally retains a
full raw copy of every USDA food record because exact reviewed-FDC resolution
later needs nutrient details. Bulk candidate discovery needs only compact
candidate metadata and the lexical token index. Keeping the full raw Foundation,
SR Legacy and FNDDS records in memory during a 1,000+ target evidence pass wastes
hundreds of MB and can force hosted runners into heavy memory pressure.

Candidate scoring is byte-compatible with ``ReferenceIndex``. Row-invariant
normalization/token metadata is precomputed privately, and the expensive
``SequenceMatcher`` ratio is evaluated only for candidates whose strict maximum
possible score can still enter the requested top-N. Private optimization metadata
never enters candidate rows, so it cannot leak into immutable evidence JSON.

This index cannot resolve nutrition profiles: ``food()`` and ``metadata()`` fail
closed.
"""
from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
import heapq
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
        """Return the exact ReferenceIndex top-N with bounded ratio evaluation.

        ``SequenceMatcher.ratio()`` contributes at most 120 points. We first
        calculate every other score component and an exact upper bound using a
        hypothetical ratio of 1.0, then visit candidates from highest upper bound
        down. Once that bound is strictly below the current Nth exact score, no
        remaining candidate can enter the top-N and ratio evaluation can stop.

        Exact score arithmetic deliberately keeps the original operation order:
        overlap terms, then sequence contribution, then phrase bonus, then the
        Foundation tie bonus. This preserves floating-point output byte-for-byte.
        """
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
        limit = max(1, int(max_candidates))

        # (maximum possible exact score, fdcId, record index, overlap base,
        #  phrase bonus, Foundation bonus)
        bounded: list[tuple[float, int, int, float, float, bool]] = []
        for index in candidate_indices:
            row = self.records[index]
            d, d_raw_tokens, d_tokens, extras, extra_tokens = self._score_rows[index]
            if not d:
                continue
            overlap = len(q_tokens & d_tokens)
            if not overlap and not (q in extras or q_tokens.intersection(extra_tokens)):
                continue

            coverage = overlap / max(1, len(q_tokens))
            precision = overlap / max(1, len(d_tokens))
            overlap_base = coverage * 400.0 + precision * 80.0

            phrase_bonus = 0.0
            if q == d:
                phrase_bonus = 1000.0
            elif q_raw_tokens and q_raw_tokens == d_raw_tokens:
                phrase_bonus = 900.0
            elif d.startswith(q) or q.startswith(d):
                phrase_bonus = 300.0
            elif q in d:
                phrase_bonus = 200.0
            foundation = row.get("dataType") == "Foundation"

            # SequenceMatcher.ratio() is in [0, 1]. Calculate the bound in the
            # same addition order as an exact score with ratio=1 so it is never
            # below any possible score for this row.
            upper = overlap_base + 120.0
            if phrase_bonus:
                upper += phrase_bonus
            if foundation:
                upper += 2.0
            bounded.append(
                (upper, int(row["fdcId"]), index, overlap_base, phrase_bonus, foundation)
            )

        bounded.sort(key=lambda item: (-item[0], item[1]))

        # Heap root is the worst retained top-N row: lower score is worse, and
        # for equal scores a larger FDC ID is worse (hence -fdcId).
        best: list[tuple[float, int, int, dict[str, Any]]] = []
        for upper, fdc_id, index, overlap_base, phrase_bonus, foundation in bounded:
            if len(best) >= limit and upper < best[0][0]:
                break

            d = self._score_rows[index][0]
            sequence = SequenceMatcher(None, q, d).ratio()
            score = overlap_base + sequence * 120.0
            if phrase_bonus:
                score += phrase_bonus
            if foundation:
                score += 2.0
            if score <= 0:
                continue

            row = self.records[index]
            entry = (score, -fdc_id, fdc_id, row)
            if len(best) < limit:
                heapq.heappush(best, entry)
            elif entry[:2] > best[0][:2]:
                heapq.heapreplace(best, entry)

        ranked = [(score, fdc_id, row) for score, _neg_id, fdc_id, row in best]
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return ranked

    def food(self, fdc_id: int) -> dict[str, Any]:
        raise RuntimeError(
            "CandidateReferenceIndex is evidence-only and cannot return raw FDC food records"
        )

    def metadata(self, fdc_id: int) -> dict[str, Any]:
        raise RuntimeError(
            "CandidateReferenceIndex is evidence-only and cannot provide resolution metadata"
        )
