#!/usr/bin/env python3
"""Snapshot recorded nutrition bindings and resume an offline review safely.

This is a structural/provenance check, NOT a semantic nutrition approval. It
never selects a candidate, modifies reviews/captures, resolves nutrients, or
activates a catalog. The output is deterministic for the same input bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

REVIEW_GLOB = "release_catalog_reviewed_nutrition_targets*.v1.json"
REVIEW_KIND = "cook4me-reviewed-nutrition-target-source"
EVIDENCE_KIND = "cook4me-fdc-review-target-candidate-evidence-offline-v60"
REQUIRED_POLICY = {
    "searchResultAutoAccepted": False,
    "exactFdcBindingRequired": True,
    "semanticConceptGroupingReviewed": True,
    "providerIdentityInference": False,
}
HEX256 = re.compile(r"[0-9a-f]{64}\Z")
RETAINED_SCOPE = "retained-reference-record"


def retained_reference_receipt(value: dict[str, Any], row: dict[str, Any],
                               context: str) -> dict[str, Any]:
    """Expand an explicit receipt; do not infer identity from another target.

The referenced candidate is a saved FDC description, not permission to copy the
source target's nutrition decision. Each destination still needs its own review.
"""
    scope = value.get("evidenceBindingScope")
    if scope is None:
        return {}
    if scope != RETAINED_SCOPE:
        raise ValueError(f"{context}: unsupported evidenceBindingScope")
    if value.get("selectionMethod") != "explicit-semantic-review":
        raise ValueError(f"{context}: retained reference requires explicit semantic review")
    if value.get("policy", {}).get("candidateSearchIsIdentityProof") is not False:
        raise ValueError(f"{context}: candidate search cannot prove identity")
    sha = _text(value, "sourceEvidenceSha256", context)
    if not HEX256.fullmatch(sha):
        raise ValueError(f"{context}: invalid source evidence SHA-256")
    receipts = value.get("referenceReceipts")
    fdc_id = _positive_int(row, "fdcId", context)
    receipt = receipts.get(str(fdc_id)) if isinstance(receipts, dict) else None
    if not isinstance(receipt, dict):
        raise ValueError(f"{context}: missing exact FDC reference receipt")
    # The rank belongs to the source record, not the destination search result.
    if "candidateEvidenceRank" in row:
        raise ValueError(f"{context}: retained-reference source rank is not a target rank")
    _text(row, "notes", context)
    _text(row, "fdcDescription", context)
    _text(row, "fdcDataType", context)
    digest = _text(receipt, "sourceCandidateSha256", context)
    if not HEX256.fullmatch(digest):
        raise ValueError(f"{context}: invalid source candidate SHA-256")
    return {
        "evidenceBindingScope": RETAINED_SCOPE,
        "sourceEvidenceSha256": sha,
        "sourceEvidenceTargetId": _text(receipt, "sourceEvidenceTargetId", context),
        "sourceEvidenceCandidateRank": _positive_int(receipt, "sourceEvidenceCandidateRank", context),
        "sourceCandidateSha256": digest,
    }


def retained_reference_mismatch(review: dict[str, Any], evidence_by_id: dict[str, Any],
                                evidence_sha256: str) -> str:
    """Check a manually recorded reference receipt against the actual saved file."""
    if review.get("sourceEvidenceSha256") != evidence_sha256:
        return "retained_reference_source_file_differs"
    source = evidence_by_id.get(review.get("sourceEvidenceTargetId"))
    if not isinstance(source, dict):
        return "retained_reference_source_target_absent"
    selected = next((c for c in source.get("candidates", [])
                     if isinstance(c, dict) and c.get("fdcId") == review["fdcId"]), None)
    if selected is None:
        return "retained_reference_fdc_id_absent"
    if any(review.get(a) != selected.get(b) for a, b in (
        ("fdcDescription", "description"), ("fdcDataType", "dataType"),
        ("sourceEvidenceCandidateRank", "localEvidenceRank"),
    )):
        return "retained_reference_candidate_metadata_differs"
    if review.get("sourceCandidateSha256") != _digest(_encoded(selected)):
        return "retained_reference_candidate_bytes_differ"
    return ""


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _encoded(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def _read(path: Path) -> tuple[dict[str, Any], str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected a regular, non-symlink input: {path}")
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path.name}")
    return value, _digest(raw)


def _text(row: dict[str, Any], key: str, context: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{context}: invalid {key}")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{context}: control character in {key}")
    return value


def _positive_int(row: dict[str, Any], key: str, context: str) -> int:
    value = row.get(key)
    if type(value) is not int or value <= 0:
        raise ValueError(f"{context}: {key} must be a positive integer")
    return value


def _identity(row: Any, context: str) -> tuple[str, str, str]:
    if not isinstance(row, dict):
        raise ValueError(f"{context}: expected an item object")
    target = _text(row, "reviewTargetId", context)
    kind = _text(row, "reviewTargetKind", context)
    name = _text(row, "canonicalEnglishName", context)
    if kind not in {"provider-identity", "semantic-concept"}:
        raise ValueError(f"{context}: unsupported reviewTargetKind")
    if (kind == "semantic-concept") != target.startswith("concept:food:"):
        raise ValueError(f"{context}: target ID/kind mismatch")
    return target, kind, name


def build_checkpoint(review_root: Path, *, source_commit: str = "") -> dict[str, Any]:
    """Read every review file; reject invalid rows and all duplicate target IDs."""
    if source_commit and not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", source_commit):
        raise ValueError("source_commit must be a full Git commit hash")
    paths = sorted(review_root.glob(REVIEW_GLOB))
    if not paths:
        raise ValueError("no nutrition review files found")
    rows: dict[str, dict[str, Any]] = {}
    files: list[dict[str, Any]] = []
    for path in paths:
        value, sha256 = _read(path)
        if type(value.get("schemaVersion")) is not int or value["schemaVersion"] != 1:
            raise ValueError(f"{path.name}: unsupported schemaVersion")
        if value.get("kind") != REVIEW_KIND:
            raise ValueError(f"{path.name}: invalid review kind")
        policy = value.get("policy")
        if not isinstance(policy, dict) or any(policy.get(k) is not v for k, v in REQUIRED_POLICY.items()):
            raise ValueError(f"{path.name}: unsafe review policy")
        if "candidateSearchIsIdentityProof" in policy and policy["candidateSearchIsIdentityProof"] is not False:
            raise ValueError(f"{path.name}: candidate search cannot be identity proof")
        manifest = value.get("referenceManifestSha256", "")
        if not isinstance(manifest, str) or (manifest and not HEX256.fullmatch(manifest)):
            raise ValueError(f"{path.name}: invalid reference manifest hash")
        items = value.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError(f"{path.name}: items must be a nonempty list")
        for index, raw in enumerate(items, 1):
            context = f"{path.name} item {index}"
            target, kind, name = _identity(raw, context)
            fdc_id = _positive_int(raw, "fdcId", context)
            if target in rows:
                raise ValueError(f"duplicate reviewTargetId {target}: {rows[target]['reviewFile']} and {path.name}")
            row = {
                "reviewTargetId": target, "reviewTargetKind": kind,
                "canonicalEnglishName": name, "fdcId": fdc_id,
                "reviewFile": path.name, "reviewFileSha256": sha256,
                "referenceManifestSha256": manifest,
                "catalogVersion": value.get("catalogVersion", ""),
            }
            for key in ("fdcDescription", "fdcDataType", "candidateEvidenceRank"):
                if key in raw:
                    row[key] = (_positive_int(raw, key, context) if key == "candidateEvidenceRank"
                                else _text(raw, key, context))
            row.update(retained_reference_receipt(value, raw, context))
            rows[target] = row
        files.append({"path": path.name, "sha256": sha256, "itemCount": len(items)})
    accepted = [rows[target] for target in sorted(rows)]
    return {
        "schemaVersion": 1, "kind": "cook4me-nutrition-review-checkpoint-v60",
        "sourceCommit": source_commit, "reviewFilesSha256": _digest(_encoded(files)),
        "recordedBindingsSha256": _digest(_encoded(accepted)),
        "summary": {"reviewFileCount": len(files), "recordedReviewTargetCount": len(accepted)},
        "policy": {"structuralValidationOnly": True, "semanticApprovalPerformed": False,
                   "candidateSelectionPerformed": False, "networkRequestsPerformed": False,
                   "sourceFilesModified": False, "catalogActivationPerformed": False},
        "reviewFiles": files, "recordedBindings": accepted,
    }


def reconcile_evidence(checkpoint: dict[str, Any], evidence_path: Path) -> dict[str, Any]:
    """Subtract exact recorded IDs without using names or candidate ranks to bind."""
    evidence, sha256 = _read(evidence_path)
    if type(evidence.get("schemaVersion")) is not int or evidence["schemaVersion"] != 1 or evidence.get("kind") != EVIDENCE_KIND:
        raise ValueError("unsupported offline candidate evidence")
    policy = evidence.get("policy")
    expected = {"candidateSearchIsIdentityProof": False, "selectionPerformed": False,
                "searchResultAutoAccepted": False, "manualExactIdReviewRequired": True,
                "providerIngredientIdentityInference": False, "networkRequestsPerformed": False}
    if not isinstance(policy, dict) or any(policy.get(k) is not v for k, v in expected.items()):
        raise ValueError("offline evidence has unsafe policy")
    manifest = _text(evidence, "referenceManifestSha256", "evidence")
    if not HEX256.fullmatch(manifest):
        raise ValueError("invalid evidence reference manifest hash")
    items = evidence.get("items")
    if not isinstance(items, list):
        raise ValueError("evidence items must be a list")
    evidence_by_id = {}
    for raw in items:
        target, _kind, _name = _identity(raw, "evidence")
        if target in evidence_by_id:
            raise ValueError(f"duplicate evidence reviewTargetId: {target}")
        evidence_by_id[target] = raw
    recorded = {r["reviewTargetId"]: r for r in checkpoint["recordedBindings"]}
    seen: set[str] = set()
    remaining: list[dict[str, Any]] = []
    mismatches: list[dict[str, str]] = []
    matched = 0
    for index, raw in enumerate(items, 1):
        target, kind, name = _identity(raw, f"evidence item {index}")
        if target in seen:
            raise ValueError(f"duplicate evidence reviewTargetId: {target}")
        seen.add(target)
        candidates = raw.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError(f"{target}: candidates must be a list")
        candidate_ids: set[int] = set()
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError(f"{target}: invalid candidate")
            fdc_id = _positive_int(candidate, "fdcId", target)
            _text(candidate, "description", target)
            _text(candidate, "dataType", target)
            _positive_int(candidate, "localEvidenceRank", target)
            if fdc_id in candidate_ids:
                raise ValueError(f"{target}: duplicate candidate fdcId")
            candidate_ids.add(fdc_id)
        review = recorded.get(target)
        if review is None:
            remaining.append(raw)
            continue
        matched += 1
        reason = ""
        if (review["reviewTargetKind"], review["canonicalEnglishName"]) != (kind, name):
            reason = "recorded_target_identity_differs"
        elif review["referenceManifestSha256"] != manifest:
            reason = "recorded_reference_manifest_differs"
        elif review["catalogVersion"] != evidence.get("catalogVersion"):
            reason = "recorded_catalog_version_differs"
        elif review.get("evidenceBindingScope") == RETAINED_SCOPE:
            reason = retained_reference_mismatch(review, evidence_by_id, sha256)
        else:
            selected = next((c for c in candidates if c["fdcId"] == review["fdcId"]), None)
            if selected is None:
                reason = "recorded_fdc_id_absent_from_target_evidence"
            elif any(review.get(a) != selected.get(b) for a, b in (
                ("fdcDescription", "description"), ("fdcDataType", "dataType"),
                ("candidateEvidenceRank", "localEvidenceRank"),
            )):
                reason = "recorded_candidate_metadata_differs"
        if reason:
            mismatches.append({"reviewTargetId": target, "reviewFile": review["reviewFile"], "reason": reason})
    return {
        "schemaVersion": 1, "kind": "cook4me-nutrition-review-resume-v60",
        "reviewFilesSha256": checkpoint["reviewFilesSha256"], "evidenceSha256": sha256,
        "referenceManifestSha256": manifest, "catalogVersion": evidence.get("catalogVersion", ""),
        "summary": {"evidenceTargetCount": len(items), "recordedTargetsInEvidence": matched,
                    "recordedTargetsOutsideEvidence": len(recorded.keys() - seen),
                    "remainingEvidenceTargetCount": len(remaining), "provenanceMismatchCount": len(mismatches)},
        "readyForManualReview": not mismatches,
        "semanticApprovalPerformed": False, "selectionPerformed": False,
        "provenanceMismatches": mismatches, "remaining": remaining,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--source-commit", default="", help="Optional full hash supplied by the caller; not independently verified")
    parser.add_argument("--evidence", type=Path, help="Existing pinned offline candidate JSON; never fetched")
    parser.add_argument("--output", type=Path, required=True, help="New output directory (must not exist)")
    args = parser.parse_args(argv)
    try:
        checkpoint = build_checkpoint(args.review_root, source_commit=args.source_commit)
        resume = reconcile_evidence(checkpoint, args.evidence) if args.evidence else None
        # A fresh directory avoids overwriting captures, reviews, or prior checkpoints.
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "checkpoint.json").write_bytes(_encoded(checkpoint))
        if resume is not None:
            (args.output / "resume.json").write_bytes(_encoded(resume))
        summary = dict(checkpoint["summary"])
        if resume is not None:
            summary.update(resume["summary"])
        (args.output / "summary.json").write_bytes(_encoded(summary))
        print(json.dumps(summary, sort_keys=True))
        return 2 if resume is not None and not resume["readyForManualReview"] else 0
    except (OSError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
