#!/usr/bin/env python3
"""Lightweight candidate-only USDA FDC index for post-activation review evidence.

The normal :class:`fdc_reference_data_v60.ReferenceIndex` intentionally retains a
full raw copy of every USDA food record because exact reviewed-FDC resolution
later needs nutrient details. Bulk candidate discovery needs only compact
candidate metadata and the lexical token index. Keeping the full raw Foundation,
SR Legacy and FNDDS records in memory during a 1,000+ target evidence pass wastes
hundreds of MB and can force hosted runners into heavy memory pressure.

This class preserves the exact candidate scoring/search implementation by
subclassing ``ReferenceIndex`` and changing only construction/storage. It cannot
be used to resolve nutrition profiles: ``food()`` and ``metadata()`` fail closed.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import fdc_reference_data_v60 as reference


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

            # Crucial difference from ReferenceIndex: no raw USDA row survives
            # this dataset iteration. The next payload may therefore reclaim it.
            del payload

        self.indexed_fdc_id_count = len(seen_fdc_ids)

    def food(self, fdc_id: int) -> dict[str, Any]:
        raise RuntimeError(
            "CandidateReferenceIndex is evidence-only and cannot return raw FDC food records"
        )

    def metadata(self, fdc_id: int) -> dict[str, Any]:
        raise RuntimeError(
            "CandidateReferenceIndex is evidence-only and cannot provide resolution metadata"
        )
