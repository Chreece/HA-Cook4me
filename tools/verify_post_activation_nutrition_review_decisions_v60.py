#!/usr/bin/env python3
"""Verify committed post-activation nutrition decisions and compiled reviews.

The verifier is offline and fail-closed. For every committed post-activation
decision artifact it resolves the exact candidate-evidence snapshot named by the
decision's ``sourceEvidenceSha256``, recompiles the corresponding reviewed-target
source, and requires the committed review file to be byte-identical to compiler
output. Multiple immutable evidence generations may coexist; a decision can
never be silently replayed against a newer snapshot.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import compile_release_catalog_fdc_review_decisions_v60 as direct  # type: ignore  # noqa: E402
import compile_release_catalog_fdc_retained_review_decisions_v60 as retained  # type: ignore  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as checkpoint  # type: ignore  # noqa: E402

DECISION_GLOB = "release_catalog_nutrition_review_decisions_post_activation_*.v1.json"
REVIEW_GLOB = "release_catalog_reviewed_nutrition_targets*.v1.json"
DECISION_RE = re.compile(
    r"release_catalog_nutrition_review_decisions_post_activation_(?P<batch>[0-9A-Za-z_-]+)\.v1\.json\Z"
)


def _review_path(review_root: Path, decision_path: Path) -> Path:
    match = DECISION_RE.fullmatch(decision_path.name)
    if match is None:
        raise ValueError(f"unsupported post-activation decision filename: {decision_path.name}")
    return review_root / f"release_catalog_reviewed_nutrition_targets_{match.group('batch')}.v1.json"


def _duplicate_review_targets(review_root: Path) -> list[tuple[str, list[str]]]:
    origins: dict[str, list[str]] = defaultdict(list)
    for path in sorted(review_root.glob(REVIEW_GLOB)):
        if path.is_symlink() or not path.is_file():
            continue
        value, _sha = checkpoint._read(path)
        items = value.get("items")
        if not isinstance(items, list):
            continue
        for raw in items:
            if not isinstance(raw, dict):
                continue
            target = str(raw.get("reviewTargetId") or "").strip()
            if target:
                origins[target].append(path.name)
    return sorted(
        (target, files)
        for target, files in origins.items()
        if len(files) > 1
    )


def _load_evidence_snapshots(
    evidence_paths: Path | Iterable[Path],
) -> dict[str, dict[str, Any]]:
    paths = [evidence_paths] if isinstance(evidence_paths, Path) else list(evidence_paths)
    if not paths:
        raise ValueError("at least one evidence snapshot is required")
    snapshots: dict[str, dict[str, Any]] = {}
    for path in paths:
        path = Path(path).expanduser()
        evidence, evidence_sha = checkpoint._read(path)
        direct._validate_evidence(evidence)
        existing = snapshots.get(evidence_sha)
        if existing is not None:
            continue
        snapshots[evidence_sha] = {
            "path": path,
            "value": evidence,
            "sourceEvidenceSha256": evidence_sha,
            "catalogVersion": checkpoint._text(evidence, "catalogVersion", path.name),
            "referenceManifestSha256": checkpoint._text(
                evidence, "referenceManifestSha256", path.name
            ),
        }
    return snapshots


def verify(
    evidence_paths: Path | Iterable[Path],
    decision_root: Path,
    review_root: Path,
) -> dict[str, Any]:
    snapshots = _load_evidence_snapshots(evidence_paths)

    decision_paths = sorted(decision_root.glob(DECISION_GLOB))
    if not decision_paths:
        raise ValueError("no post-activation nutrition decision files found")

    duplicates = _duplicate_review_targets(review_root)
    if duplicates:
        detail = "; ".join(
            f"{target}: {', '.join(files)}"
            for target, files in duplicates
        )
        raise ValueError("duplicate reviewTargetIds: " + detail)

    global_checkpoint = checkpoint.build_checkpoint(review_root)
    checkpoint_ids = {
        row["reviewTargetId"] for row in global_checkpoint["recordedBindings"]
    }

    batches: list[dict[str, Any]] = []
    target_ids: set[str] = set()
    binding_count = 0
    used_snapshot_counts: CounterLike = defaultdict(int)

    for decision_path in decision_paths:
        decisions, decision_sha = checkpoint._read(decision_path)
        requested_evidence_sha = checkpoint._text(
            decisions, "sourceEvidenceSha256", decision_path.name
        )
        snapshot = snapshots.get(requested_evidence_sha)
        if snapshot is None:
            raise ValueError(
                f"{decision_path.name}: no supplied evidence snapshot matches "
                f"sourceEvidenceSha256 {requested_evidence_sha}"
            )
        evidence = snapshot["value"]
        evidence_sha = snapshot["sourceEvidenceSha256"]
        used_snapshot_counts[evidence_sha] += 1

        kind = decisions.get("kind")
        if kind == direct.DECISIONS_KIND:
            payload, summary = direct.compile_review_source(
                evidence,
                decisions,
                evidence_sha256=evidence_sha,
                decisions_sha256=decision_sha,
            )
            compiler_kind = "direct-target-candidate"
        elif kind == retained.DECISIONS_KIND:
            payload, summary = retained.compile_review_source(
                evidence,
                decisions,
                evidence_sha256=evidence_sha,
                decisions_sha256=decision_sha,
            )
            compiler_kind = "retained-reference-record"
        else:
            raise ValueError(f"{decision_path.name}: unsupported decision kind {kind!r}")

        review_path = _review_path(review_root, decision_path)
        if review_path.is_symlink() or not review_path.is_file():
            raise ValueError(f"{decision_path.name}: compiled review file is missing: {review_path.name}")
        committed = review_path.read_bytes()
        expected = checkpoint._encoded(payload)
        if committed != expected:
            raise ValueError(
                f"{decision_path.name}: {review_path.name} is not byte-identical to compiler output"
            )

        batch_ids: list[str] = []
        for row in payload.get("items") or []:
            target = checkpoint._text(row, "reviewTargetId", decision_path.name)
            if target in target_ids:
                raise ValueError(f"duplicate post-activation decision target: {target}")
            if target not in checkpoint_ids:
                raise ValueError(f"compiled target missing from global checkpoint: {target}")
            target_ids.add(target)
            batch_ids.append(target)
        binding_count += len(batch_ids)
        batches.append(
            {
                "decisionFile": decision_path.name,
                "reviewFile": review_path.name,
                "compilerKind": compiler_kind,
                "sourceEvidenceSha256": evidence_sha,
                "referenceManifestSha256": snapshot["referenceManifestSha256"],
                "decisionSha256": decision_sha,
                "reviewSha256": checkpoint._digest(committed),
                "compiledBindingCount": len(batch_ids),
                "usageCountAtReview": sum(
                    max(0, int(row.get("usageCountAtReview") or 0))
                    for row in payload.get("items") or []
                    if isinstance(row, dict)
                ),
                "automaticSelectionCount": int(summary.get("automaticSelectionCount") or 0),
            }
        )

    if any(batch["automaticSelectionCount"] != 0 for batch in batches):
        raise ValueError("a post-activation compiler reported automatic selection")

    snapshot_rows = [
        {
            "sourceEvidenceSha256": sha,
            "catalogVersion": snapshot["catalogVersion"],
            "referenceManifestSha256": snapshot["referenceManifestSha256"],
            "fileName": snapshot["path"].name,
            "decisionBatchCount": int(used_snapshot_counts.get(sha, 0)),
        }
        for sha, snapshot in sorted(snapshots.items())
    ]
    used_rows = [row for row in snapshot_rows if row["decisionBatchCount"] > 0]
    catalog_versions = sorted({row["catalogVersion"] for row in used_rows})
    manifest_shas = sorted({row["referenceManifestSha256"] for row in used_rows})
    evidence_shas = sorted({row["sourceEvidenceSha256"] for row in used_rows})

    return {
        "schemaVersion": 1,
        "kind": "cook4me-post-activation-nutrition-review-verification-v60",
        "catalogVersion": catalog_versions[0] if len(catalog_versions) == 1 else "",
        "catalogVersions": catalog_versions,
        "referenceManifestSha256": manifest_shas[0] if len(manifest_shas) == 1 else "",
        "referenceManifestSha256s": manifest_shas,
        "sourceEvidenceSha256": evidence_shas[0] if len(evidence_shas) == 1 else "",
        "sourceEvidenceSha256s": evidence_shas,
        "suppliedEvidenceSnapshotCount": len(snapshot_rows),
        "usedEvidenceSnapshotCount": len(used_rows),
        "decisionBatchCount": len(batches),
        "compiledBindingCount": binding_count,
        "usageCountAtReview": sum(batch["usageCountAtReview"] for batch in batches),
        "globalReviewFileCount": global_checkpoint["summary"]["reviewFileCount"],
        "globalRecordedReviewTargetCount": global_checkpoint["summary"]["recordedReviewTargetCount"],
        "automaticSelectionCount": 0,
        "searchResultsAutoAccepted": False,
        "networkRequestsPerformed": False,
        "sourceFilesModified": False,
        "evidenceSnapshots": snapshot_rows,
        "batches": batches,
    }


CounterLike = dict[str, int]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence",
        type=Path,
        required=True,
        action="append",
        help="Exact immutable candidate-evidence file; repeat for multiple generations",
    )
    parser.add_argument("--decision-root", type=Path, default=TOOLS)
    parser.add_argument("--review-root", type=Path, default=TOOLS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        summary = verify(
            [path.expanduser() for path in args.evidence],
            args.decision_root.expanduser(),
            args.review_root.expanduser(),
        )
        if args.output is not None:
            output = args.output.expanduser()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(checkpoint._encoded(summary))
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
