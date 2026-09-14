#!/usr/bin/env python3
"""Compatibility entry point for the v60 nutrition queue classifier.

The frozen Batch-47 classifier remains in ``classify_nutrition_review_queue_v60_base``.
Additional fail-closed identity ambiguity rules are layered in here so later tiny
triage batches can extend one small dedicated rule module without rewriting the
classifier core.
"""
from __future__ import annotations

import classify_nutrition_review_queue_v60_base as _base
import nutrition_review_identity_ambiguities_v60 as identity_ambiguities

# Re-export the frozen module's API (including helper modules used by regressions).
for _name, _value in vars(_base).items():
    if _name not in {"classify", "main", "__name__", "__file__", "__package__", "__spec__"}:
        globals()[_name] = _value

_BASE_CLASSIFY = _base.classify
_BASE_MAIN = _base.main


def classify(evidence_path, *, review_root=TOOLS):
    """Run the frozen classifier with the additional identity-ambiguity registry."""
    original_partition = _base._partition_remaining

    def partition_with_additional_ambiguities(rows, compiled, **kwargs):
        existing = tuple(kwargs.get("identity_ambiguities") or ())
        kwargs["identity_ambiguities"] = existing + tuple(identity_ambiguities.RULES)
        return original_partition(rows, compiled, **kwargs)

    _base._partition_remaining = partition_with_additional_ambiguities
    try:
        return _BASE_CLASSIFY(evidence_path, review_root=review_root)
    finally:
        _base._partition_remaining = original_partition


def main(argv=None):
    """Preserve the original CLI while routing it through the layered classifier."""
    original_classify = _base.classify
    _base.classify = classify
    try:
        return _BASE_MAIN(argv)
    finally:
        _base.classify = original_classify


if __name__ == "__main__":
    raise SystemExit(main())
