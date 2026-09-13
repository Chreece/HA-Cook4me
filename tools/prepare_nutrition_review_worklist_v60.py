#!/usr/bin/env python3
"""Prepare an offline evidence worklist without approving nutrition bindings.

A deferred target is still unresolved. Lexical reference lookup is navigation,
not semantic proof. This tool never changes review files, holds or input data.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

import nutrition_review_holds_v60 as holds
import snapshot_nutrition_review_checkpoint_v60 as checkpoint

TOOLS = Path(__file__).resolve().parent
LEDGER = TOOLS / "release_catalog_nutrition_review_blockers.v1.json"
KIND = "cook4me-nutrition-evidence-requirements-v60"
POLICY = {
    "bindingsApproved": False,
    "heldBindingsReleased": False,
    "deferredTargetsCountAsComplete": False,
    "lexicalSearchIsIdentityProof": False,
    "providerIdentityInference": False,
    "sourceFilesModified": False,
}
REASONS = {
    "compound-without-proportions", "identity-unspecified",
    "state-or-formulation-unspecified", "retained-reference-not-established",
}


def validate_ledger(
    ledger: dict[str, Any], evidence: dict[str, Any], evidence_sha: str,
) -> dict[str, dict[str, Any]]:
    """Validate full identities and exact original row bytes, not similar names."""
    if (type(ledger.get("schemaVersion")) is not int or ledger["schemaVersion"] != 1
            or ledger.get("kind") != KIND):
        raise ValueError("unsupported evidence-requirement ledger")
    policy = ledger.get("policy")
    if not isinstance(policy, dict) or any(policy.get(k) is not v for k, v in POLICY.items()):
        raise ValueError("unsafe evidence-requirement policy")
    if not checkpoint.HEX256.fullmatch(evidence_sha):
        raise ValueError("invalid evidence SHA-256")
    if ledger.get("sourceEvidenceSha256") != evidence_sha:
        raise ValueError("ledger requires the exact retained evidence file")
    for key in ("catalogVersion", "referenceManifestSha256"):
        checkpoint._text(ledger, key, "ledger")
        if ledger[key] != evidence.get(key):
            raise ValueError(f"ledger {key} drift")
    items = ledger.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("ledger items must be a nonempty list")
    original: dict[str, dict[str, Any]] = {}
    for raw in evidence.get("items", []):
        target, _kind, _name = checkpoint._identity(raw, "evidence")
        if target in original:
            raise ValueError(f"duplicate evidence target: {target}")
        original[target] = raw
    out: dict[str, dict[str, Any]] = {}
    for raw in items:
        target, kind, name = checkpoint._identity(raw, "ledger item")
        if target in out:
            raise ValueError(f"duplicate ledger target: {target}")
        if raw.get("disposition") != "deferred-no-binding" or raw.get("reasonCode") not in REASONS:
            raise ValueError(f"invalid ledger disposition/reason: {target}")
        if any(k in raw for k in ("fdcId", "selectedFdcId", "candidateEvidenceRank")):
            raise ValueError(f"a deferred requirement cannot select an FDC binding: {target}")
        for key in ("reason", "evidenceRequired", "referenceQuery"):
            checkpoint._text(raw, key, target)
        row = original.get(target)
        if row is None or (row["reviewTargetKind"], row["canonicalEnglishName"]) != (kind, name):
            raise ValueError(f"ledger target identity drift: {target}")
        if raw.get("sourceTargetSha256") != checkpoint._digest(checkpoint._encoded(row)):
            raise ValueError(f"ledger target evidence bytes drift: {target}")
        if type(raw.get("usageCountAtReview")) is not int or raw["usageCountAtReview"] != row.get("usageCountSum"):
            raise ValueError(f"ledger usage evidence drift: {target}")
        out[target] = deepcopy(raw)
    return out


def build_reference_index(evidence: dict[str, Any], held_ids: set[str]) -> dict[str, Any]:
    """Index exact FDC IDs and all retrieval occurrences; do not choose a locator."""
    indexed: dict[int, dict[str, Any]] = {}
    seen_targets: set[str] = set()
    occurrence_count = 0
    for raw in evidence.get("items", []):
        target, _kind, _name = checkpoint._identity(raw, "reference source")
        if target in seen_targets:
            raise ValueError(f"duplicate reference source target: {target}")
        seen_targets.add(target)
        candidates = raw.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError(f"invalid reference candidates: {target}")
        seen_ids: set[int] = set()
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError(f"invalid reference record: {target}")
            fdc_id = checkpoint._positive_int(candidate, "fdcId", target)
            if fdc_id in seen_ids:
                raise ValueError(f"duplicate candidate ID: {target}")
            seen_ids.add(fdc_id)
            description = checkpoint._text(candidate, "description", target)
            data_type = checkpoint._text(candidate, "dataType", target)
            rank = checkpoint._positive_int(candidate, "localEvidenceRank", target)
            record = indexed.setdefault(fdc_id, {"fdcId": fdc_id, "occurrences": []})
            record["occurrences"].append({
                "sourceEvidenceTargetId": target, "sourceEvidenceCandidateRank": rank,
                "sourceCandidateSha256": checkpoint._digest(checkpoint._encoded(candidate)),
                "description": description, "dataType": data_type,
                "sourceTargetHeld": target in held_ids,
            })
            occurrence_count += 1
    records = []
    for fdc_id in sorted(indexed):
        row = indexed[fdc_id]
        row["occurrences"].sort(key=lambda x: (x["sourceEvidenceTargetId"], x["sourceEvidenceCandidateRank"]))
        records.append(row)
    return {"schemaVersion": 1, "kind": "cook4me-retained-reference-navigation-index-v60",
            "referenceRecordCount": len(records), "candidateOccurrenceCount": occurrence_count,
            "selectionPerformed": False, "semanticApprovalPerformed": False, "records": records}


def search_references(index: dict[str, Any], query: str) -> dict[str, Any]:
    """Case-insensitive AND substring lookup; neither rank nor a prior review votes."""
    terms = query.casefold().split()
    if not terms:
        raise ValueError("reference query must not be empty")
    matches = []
    excluded = 0
    for row in index["records"]:
        occurrences = []
        for location in row["occurrences"]:
            if not all(term in location["description"].casefold() for term in terms):
                continue
            if location["sourceTargetHeld"]:
                excluded += 1
                continue
            occurrences.append(deepcopy(location))
        if occurrences:
            matches.append({"fdcId": row["fdcId"], "occurrences": occurrences})
    return {"query": query, "matchRecordCount": len(matches),
            "heldLocatorOccurrencesExcluded": excluded, "matches": matches,
            "selectionPerformed": False, "lexicalSearchIsIdentityProof": False,
            "zeroMatchesProveFoodAbsent": False}


def partition_requirements(
    ledger: dict[str, dict[str, Any]], remaining: list[dict[str, Any]],
    recorded: dict[str, dict[str, Any]], held_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep deferrals visible and never make a later recorded decision an approval."""
    remaining_ids = {r["reviewTargetId"] for r in remaining}
    if len(remaining_ids) != len(remaining) or remaining_ids & recorded.keys():
        raise ValueError("remaining queue duplicates or overlaps recorded target IDs")
    annotated = []
    for target, requirement in ledger.items():
        if target in held_ids:
            status = "held-requires-separate-rereview"
        elif target in recorded:
            status = "recorded-later-not-certified-by-this-ledger"
        elif target in remaining_ids:
            status = "unreviewed-needs-evidence"
        else:
            raise ValueError(f"ledger target absent from current work partitions: {target}")
        annotated.append({**deepcopy(requirement), "currentStatus": status})
    # This is only an investigation view, never a replacement completeness queue.
    untriaged = [deepcopy(r) for r in remaining if r["reviewTargetId"] not in ledger]
    return annotated, untriaged


def build_outputs(evidence_path: Path, *, review_root: Path = TOOLS,
                  ledger_path: Path = LEDGER, queries: list[str] | None = None) -> dict[str, Any]:
    """Always execute the real hold/provenance audit before preparing work views."""
    audit = holds.audit(evidence_path, review_root=review_root,
                        registry_path=review_root / holds.REGISTRY.name)
    evidence, evidence_sha = checkpoint._read(evidence_path)
    if evidence_sha != audit["evidenceSha256"]:
        raise ValueError("evidence changed during audit")
    raw_ledger, ledger_sha = checkpoint._read(ledger_path)
    ledger = validate_ledger(raw_ledger, evidence, evidence_sha)
    baseline = checkpoint.build_checkpoint(review_root)
    if baseline["reviewFilesSha256"] != audit["reviewFilesSha256"]:
        raise ValueError("review files changed during audit")
    recorded = {r["reviewTargetId"]: r for r in baseline["recordedBindings"]}
    held_ids = {r["reviewTargetId"] for r in audit["heldTargets"]}
    remaining = audit["remainingUnheldCandidates"]
    annotated, untriaged = partition_requirements(ledger, remaining, recorded, held_ids)
    unresolved = [r for r in annotated if r["currentStatus"] == "unreviewed-needs-evidence"]
    index = build_reference_index(evidence, held_ids)
    index["sourceEvidenceSha256"] = evidence_sha
    index["holdRegistrySha256"] = audit["registrySha256"]
    lookups = queries if queries else sorted({r["referenceQuery"] for r in ledger.values()})
    searches = [search_references(index, q) for q in lookups]
    summary = {**audit["summary"], "evidenceRequirementCount": len(ledger),
               "unresolvedRequirementCount": len(unresolved),
               "untriagedCandidateCount": len(untriaged),
               "retainedReferenceRecordCount": index["referenceRecordCount"],
               "candidateOccurrenceCount": index["candidateOccurrenceCount"],
               "newBindingsApproved": 0}
    worklist = {"schemaVersion": 1, "kind": "cook4me-nutrition-evidence-worklist-v60",
                "summary": summary, "sourceEvidenceSha256": evidence_sha,
                "reviewFilesSha256": baseline["reviewFilesSha256"],
                "recordedBindingsSha256": baseline["recordedBindingsSha256"],
                "requirementLedgerSha256": ledger_sha, "holdRegistrySha256": audit["registrySha256"],
                "readyForManualReview": audit["readyForManualReview"],
                "readyForUnheldManualReview": audit["readyForUnheldManualReview"],
                "catalogNutritionApprovalGranted": False, "policy": dict(POLICY),
                "requirements": annotated}
    queue = {"kind": "cook4me-unreviewed-retained-candidate-queue",
             "sourceEvidenceSha256": evidence_sha, "items": deepcopy(remaining)}
    return {"summary.json": summary, "worklist.json": worklist, "hold-audit.json": audit,
            "checkpoint.json": baseline, "reference-index.json": index,
            "reference-search.json": {"selectionPerformed": False, "searches": searches},
            "remaining.json": queue,
            "untriaged.json": {"kind": "cook4me-investigation-view-not-completeness-queue",
                               "sourceEvidenceSha256": evidence_sha, "items": untriaged}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New report directory; never overwritten")
    parser.add_argument("--query", action="append", help="Literal AND terms in reference descriptions; repeatable")
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("output directory must not exist")
        outputs = build_outputs(args.evidence, queries=args.query)
        args.output.mkdir(parents=True, exist_ok=False)
        for name, value in outputs.items():
            (args.output / name).write_bytes(checkpoint._encoded(value))
        summary = outputs["summary.json"]
        print(json.dumps(summary, sort_keys=True))
        # Report generation success is distinct from nutrition readiness.
        return 2 if (summary["remainingEvidenceTargetCount"]
                     or summary["heldReviewTargetCount"]
                     or summary["unheldProvenanceMismatchCount"]) else 0
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
