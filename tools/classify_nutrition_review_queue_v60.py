#!/usr/bin/env python3
"""Classify the remaining v60 nutrition queue for fast evidence-first review.

Committed family rules are approval rules only when an explicit reviewed target
row exists. This tool never creates a binding. It orders the unresolved queue
into manual-family candidates (B) and context-heavy blockers (C).
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from typing import Any

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import nutrition_review_holds_v60 as holds  # noqa: E402
import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as cp  # noqa: E402

RULES = TOOLS / "release_catalog_nutrition_bulk_family_rules.v1.json"
REVIEW_FILES = tuple(TOOLS / name for name in (
    "release_catalog_reviewed_nutrition_targets_041.v1.json",
    "release_catalog_reviewed_nutrition_targets_041b.v1.json",
    "release_catalog_reviewed_nutrition_targets_041c.v1.json",
    "release_catalog_reviewed_nutrition_targets_041d.v1.json",
    "release_catalog_reviewed_nutrition_targets_041e.v1.json",
    "release_catalog_reviewed_nutrition_targets_041f.v1.json",
))
COMPLEX = re.compile(
    r"\b(?:and|or|mix|blend|seasoning|spices?|stock|bouillon|broth|sauce|paste|roux|soup|"
    r"brine|soak(?:ed|ing)?|marinat(?:ed|ing)|cured|smoked|cooked|boiled|fried|roasted|"
    r"toasted|dehydrated|dried|frozen|canned|pickled|preserve|syrup|extract|flavou?r|"
    r"concentrat(?:e|ed)|liquid|cream|fat|combined|stuffed|ready-made|store-bought|"
    r"commercial|unknown|water or|or water)\b",
    re.IGNORECASE,
)


def _load_rules(path: Path = RULES) -> tuple[dict[str, Any], list[tuple[dict[str, Any], re.Pattern[str]]]]:
    doc, _sha = cp._read(path)
    if doc.get("kind") != "cook4me-nutrition-bulk-family-rules-v60" or doc.get("schemaVersion") != 1:
        raise ValueError("invalid bulk-family rule registry")
    policy = doc.get("policy") if isinstance(doc.get("policy"), dict) else {}
    required = {
        "ruleMatchIsApprovalOnlyWhenReviewRowExists": True,
        "regexAnchoredRequired": True,
        "multipleRuleMatchesRejected": True,
        "heldTargetsExcluded": True,
        "candidateRankIsIdentityProof": False,
        "providerIdentityInference": False,
        "automaticRuleExpansionForbidden": True,
    }
    if any(policy.get(k) is not v for k, v in required.items()):
        raise ValueError("unsafe bulk-family policy")
    compiled = []
    seen = set()
    for raw in doc.get("rules") or []:
        if not isinstance(raw, dict):
            raise ValueError("bulk-family rule must be an object")
        ident = cp._text(raw, "ruleId", "bulk rule")
        pattern = cp._text(raw, "pattern", ident)
        if ident in seen:
            raise ValueError(f"duplicate bulk-family rule: {ident}")
        seen.add(ident)
        if not pattern.startswith("^") or not pattern.endswith("$"):
            raise ValueError(f"bulk-family rule must be fully anchored: {ident}")
        if raw.get("tier") not in {"A", "B"}:
            raise ValueError(f"invalid approval tier: {ident}")
        cp._positive_int(raw, "fdcId", ident)
        cp._text(raw, "fdcDescription", ident)
        cp._text(raw, "contract", ident)
        compiled.append((raw, re.compile(pattern, re.IGNORECASE)))
    return doc, compiled


def _matches(name: str, compiled: list[tuple[dict[str, Any], re.Pattern[str]]]) -> list[dict[str, Any]]:
    return [rule for rule, regex in compiled if regex.match(name)]


def _partition_remaining(
    rows: list[dict[str, Any]],
    compiled: list[tuple[dict[str, Any], re.Pattern[str]]],
    *,
    has_candidates=None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Losslessly partition unresolved rows without selecting or approving anything.

    ``has_candidates`` exists so regression fixtures can use a compact candidate-count
    projection instead of embedding the multi-megabyte evidence file. Production calls
    use the exact retained ``candidates`` list on each row.
    """
    if has_candidates is None:
        has_candidates = lambda row: bool(row.get("candidates"))
    tier_b: list[dict[str, Any]] = []
    tier_c: list[dict[str, Any]] = []
    rule_covered_unreviewed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            raise ValueError("remaining target must be an object")
        target_id = cp._text(raw, "reviewTargetId", "remaining target")
        name = cp._text(raw, "canonicalEnglishName", target_id)
        if target_id in seen:
            raise ValueError(f"duplicate remaining target: {target_id}")
        seen.add(target_id)
        row = deepcopy(raw)
        matched = _matches(name, compiled)
        if len(matched) > 1:
            raise ValueError(f"remaining target matches multiple rules: {target_id}")
        if matched:
            row["matchedRuleId"] = matched[0]["ruleId"]
            row["classification"] = "B-rule-match-requires-explicit-review-row"
            rule_covered_unreviewed.append(row)
            continue
        if COMPLEX.search(name) or not has_candidates(raw):
            row["classification"] = "C-context-or-composition-required"
            tier_c.append(row)
        else:
            row["classification"] = "B-manual-family-candidate"
            tier_b.append(row)
    if len(tier_b) + len(tier_c) + len(rule_covered_unreviewed) != len(rows):
        raise RuntimeError("classification is not a lossless partition")
    return rule_covered_unreviewed, tier_b, tier_c


def classify(evidence_path: Path, *, review_root: Path = TOOLS) -> dict[str, Any]:
    rules_doc, compiled = _load_rules(review_root / RULES.name)
    audit = holds.audit(evidence_path, review_root=review_root,
                        registry_path=review_root / holds.REGISTRY.name)
    evidence, evidence_sha = cp._read(evidence_path)
    if evidence_sha != rules_doc.get("sourceEvidenceSha256"):
        raise ValueError("bulk-family rules target a different evidence snapshot")
    reviews = resolver.load_reviews(review_root)
    held = {r["reviewTargetId"] for r in audit["heldTargets"]}

    # Every explicit row in Batch 37 must match exactly one committed rule.
    reviewed_ids = set()
    coverage = []
    for configured in REVIEW_FILES:
        path = review_root / configured.name
        review_doc, _ = cp._read(path)
        for row in review_doc.get("items") or []:
            target_id = cp._text(row, "reviewTargetId", path.name)
            if target_id in reviewed_ids:
                raise ValueError(f"duplicate Batch 37 target: {target_id}")
            matched = _matches(cp._text(row, "canonicalEnglishName", target_id), compiled)
            if len(matched) != 1:
                raise ValueError(f"Batch 37 target must match exactly one rule: {target_id}")
            rule = matched[0]
            if row.get("bulkFamilyRuleId") != rule["ruleId"] or row.get("bulkFamilyTier") != rule["tier"]:
                raise ValueError(f"Batch 37 rule receipt differs: {target_id}")
            if row.get("fdcId") != rule["fdcId"] or row.get("fdcDescription") != rule["fdcDescription"]:
                raise ValueError(f"Batch 37 rule binding differs: {target_id}")
            if target_id in held:
                raise ValueError(f"held target cannot be bulk-reviewed: {target_id}")
            reviewed_ids.add(target_id)
            coverage.append({"reviewTargetId": target_id, "ruleId": rule["ruleId"], "tier": rule["tier"]})

    rule_covered_unreviewed, tier_b, tier_c = _partition_remaining(
        audit["remainingUnheldCandidates"], compiled
    )

    summary = {
        "recordedReviewTargetCount": audit["summary"]["recordedReviewTargetCount"],
        "heldReviewTargetCount": audit["summary"]["heldReviewTargetCount"],
        "remainingReviewTargetCount": len(audit["remainingUnheldCandidates"]),
        "batch37ExplicitReviewCount": len(reviewed_ids),
        "batch37TierACount": sum(r["tier"] == "A" for r in coverage),
        "batch37TierBCount": sum(r["tier"] == "B" for r in coverage),
        "unreviewedRuleMatchCount": len(rule_covered_unreviewed),
        "manualFamilyCandidateCount": len(tier_b),
        "contextHeavyCount": len(tier_c),
        "bindingsApprovedByClassifier": 0,
        "networkRequestsPerformed": False,
    }
    if len(tier_b) + len(tier_c) + len(rule_covered_unreviewed) != len(audit["remainingUnheldCandidates"]):
        raise RuntimeError("classification is not a lossless partition")
    return {
        "schemaVersion": 1,
        "kind": "cook4me-nutrition-review-tier-classification-v60",
        "sourceEvidenceSha256": evidence_sha,
        "reviewFilesSha256": audit["reviewFilesSha256"],
        "holdRegistrySha256": audit["registrySha256"],
        "policy": {
            "classificationIsApproval": False,
            "ruleMatchWithoutReviewRowIsApproval": False,
            "candidateRankIsIdentityProof": False,
            "networkRequestsPerformed": False,
        },
        "summary": summary,
        "batch37Coverage": coverage,
        "ruleCoveredButUnreviewed": rule_covered_unreviewed,
        "tierBManual": tier_b,
        "tierCContext": tier_c,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("output directory must not exist")
        result = classify(args.evidence)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "classification.json").write_bytes(cp._encoded(result))
        (args.output / "summary.json").write_bytes(cp._encoded(result["summary"]))
        (args.output / "tier-b-manual.json").write_bytes(cp._encoded({"items": result["tierBManual"]}))
        (args.output / "tier-c-context.json").write_bytes(cp._encoded({"items": result["tierCContext"]}))
        print(json.dumps(result["summary"], sort_keys=True))
        return 2 if result["summary"]["remainingReviewTargetCount"] else 0
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
