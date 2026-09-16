from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
from typing import Any

_NUMBERED_REVIEW = re.compile(
    r"^release_catalog_reviewed_nutrition_targets_(\d{3})\.v1\.json$"
)


def _encoded(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_encoded(value)).hexdigest()


def _is_later_numbered_review(path: str, max_numbered_batch: int) -> bool:
    match = _NUMBERED_REVIEW.fullmatch(str(path or ""))
    return bool(match and int(match.group(1)) > max_numbered_batch)


def historical_checkpoint(
    checkpoint: dict[str, Any], *, max_numbered_batch: int = 45
) -> dict[str, Any]:
    """Return the frozen pre-post-activation view of a current checkpoint.

    Historical batch-42..50 regression tests intentionally describe the review
    corpus that existed before post-activation nutrition enrichment. Exact
    numbered review files 046+ were added later and must not rewrite those frozen
    baselines. Letter-suffixed historical files (for example ``044b``) remain in
    scope because they are not post-activation numbered batches.

    The normal checkpoint builder remains unchanged and always validates the full
    current corpus. This helper is opt-in and should only be used by tests that
    explicitly assert a historical baseline.
    """
    if max_numbered_batch < 0:
        raise ValueError("max_numbered_batch must be non-negative")

    out = deepcopy(checkpoint)
    review_files = [
        row
        for row in out.get("reviewFiles", [])
        if not _is_later_numbered_review(row.get("path", ""), max_numbered_batch)
    ]
    review_names = {row.get("path") for row in review_files}
    recorded = [
        row
        for row in out.get("recordedBindings", [])
        if row.get("reviewFile") in review_names
    ]

    out["reviewFiles"] = review_files
    out["recordedBindings"] = recorded
    out["reviewFilesSha256"] = _digest(review_files)
    out["recordedBindingsSha256"] = _digest(recorded)
    summary = dict(out.get("summary") or {})
    summary["reviewFileCount"] = len(review_files)
    summary["recordedReviewTargetCount"] = len(recorded)
    out["summary"] = summary
    return out
