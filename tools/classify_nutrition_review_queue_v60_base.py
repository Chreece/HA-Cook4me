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
import prepare_nutrition_review_worklist_v60 as worklist  # noqa: E402
import resolve_reviewed_release_catalog_nutrition_targets_v60 as resolver  # noqa: E402
import snapshot_nutrition_review_checkpoint_v60 as cp  # noqa: E402

RULES = TOOLS / "release_catalog_nutrition_bulk_family_rules.v1.json"
RULE_GLOB = "release_catalog_nutrition_bulk_family_rules*.v1.json"
GENERIC_PEPPER = re.compile(
    r"^(?:\*?pepper|ground pepper|coarsely ground pepper)"
    r"(?:\s*\((?:a little|for finishing)\))?(?:,\s*a little)?$",
    re.IGNORECASE,
)

FORMULATED_SPICE_BLEND = re.compile(
    r"^(?:curry|garam masala(?:,\s*a little)?)$",
    re.IGNORECASE,
)

FORMULATED_HERB_BLEND = re.compile(
    r"^(?:herbes de provence|italian herbs)$",
    re.IGNORECASE,
)

FORMULATED_PEPPER_SALT = re.compile(
    r"^(?:(?:a|c)- )?pepper salt(?: \(a little\)|, a little)?$",
    re.IGNORECASE,
)


COMPLEX = re.compile(
    r"\b(?:and|or|mix(?:ed|ing|tures?)?|blend(?:ed|ing)?|seasoning|spices?|stock|bouillon|broth|"
    r"sauce|paste|roux|soup|consomm[eé]|brine|soak(?:ed|ing)?|marinat(?:ed|ing)|marinades?|"
    r"cured|smoked|cooked|pre[- ]?cooked|boiled|fried|roasted|toasted|dehydrated|"
    r"rehydrat(?:ed|ing)?|dried|frozen|canned|pickled|preserv(?:e|ed|es|ing)|ferment(?:ed|ing)?|"
    r"syrup|extract|flavou?r(?:ed|ing|ings)?|concentrat(?:e|ed)|liquid|cream|fat|combined|stuffed|"
    r"ready-made|store-bought|commercial|unknown|water or|or water|slurry|pur[eé]e?s?|compotes?|"
    r"coulis|mousses?|vinaigrettes?|dressings?|starters?|dumplings?|meatballs?|candied|glazed|"
    r"food colou?r(?:ing)?|bouquet(?: garni)?|spreads?|puddings?|dough|etc)\b|&",
    re.IGNORECASE,
)


def _load_rules(path: Path | None = None) -> tuple[dict[str, Any], list[tuple[dict[str, Any], re.Pattern[str]]]]:
    paths = [path] if path is not None else sorted(TOOLS.glob(RULE_GLOB))
    if not paths:
        raise ValueError("missing bulk-family rule registry")
    compiled = []
    seen = set()
    aggregate = None
    required = {
        "ruleMatchIsApprovalOnlyWhenReviewRowExists": True,
        "regexAnchoredRequired": True,
        "multipleRuleMatchesRejected": True,
        "heldTargetsExcluded": True,
        "candidateRankIsIdentityProof": False,
        "providerIdentityInference": False,
        "automaticRuleExpansionForbidden": True,
    }
    for registry in paths:
        doc, _sha = cp._read(registry)
        if doc.get("kind") != "cook4me-nutrition-bulk-family-rules-v60" or doc.get("schemaVersion") != 1:
            raise ValueError(f"invalid bulk-family rule registry: {registry.name}")
        policy = doc.get("policy") if isinstance(doc.get("policy"), dict) else {}
        if any(policy.get(k) is not v for k, v in required.items()):
            raise ValueError(f"unsafe bulk-family policy: {registry.name}")
        if aggregate is None:
            aggregate = {**doc, "rules": [], "registries": []}
        elif (doc.get("catalogVersion") != aggregate.get("catalogVersion") or
              doc.get("sourceEvidenceSha256") != aggregate.get("sourceEvidenceSha256") or
              doc.get("referenceManifestSha256") != aggregate.get("referenceManifestSha256")):
            raise ValueError(f"bulk-family registry provenance differs: {registry.name}")
        aggregate["registries"].append(registry.name)
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
            aggregate["rules"].append(raw)
            compiled.append((raw, re.compile(pattern, re.IGNORECASE)))
    return aggregate, compiled


def _matches(name: str, compiled: list[tuple[dict[str, Any], re.Pattern[str]]]) -> list[dict[str, Any]]:
    return [rule for rule, regex in compiled if regex.match(name)]


def _partition_remaining(
    rows: list[dict[str, Any]],
    compiled: list[tuple[dict[str, Any], re.Pattern[str]]],
    *,
    has_candidates=None,
    evidence_requirements: dict[str, dict[str, Any]] | None = None,
    identity_ambiguities: tuple[tuple[str, re.Pattern[str]], ...] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Losslessly partition unresolved rows without selecting or approving anything.

    ``has_candidates`` exists so regression fixtures can use a compact candidate-count
    projection instead of embedding the multi-megabyte evidence file. Production calls
    use the exact retained ``candidates`` list on each row.
    """
    if has_candidates is None:
        has_candidates = lambda row: bool(row.get("candidates"))
    if evidence_requirements is None:
        evidence_requirements = {}
    if identity_ambiguities is None:
        identity_ambiguities = ()
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
        requirement = evidence_requirements.get(target_id)
        if requirement is not None:
            if not isinstance(requirement, dict):
                raise ValueError(f"invalid evidence requirement: {target_id}")
            row["classification"] = "C-explicit-evidence-requirement"
            row["evidenceRequirementReasonCode"] = cp._text(
                requirement, "reasonCode", target_id
            )
            tier_c.append(row)
            continue
        matched = _matches(name, compiled)
        if len(matched) > 1:
            raise ValueError(f"remaining target matches multiple rules: {target_id}")
        if matched:
            row["matchedRuleId"] = matched[0]["ruleId"]
            row["classification"] = "B-rule-match-requires-explicit-review-row"
            rule_covered_unreviewed.append(row)
            continue
        ambiguity_matches = [
            classification
            for classification, pattern in identity_ambiguities
            if pattern.match(name)
        ]
        if len(ambiguity_matches) > 1:
            raise ValueError(f"remaining target matches multiple identity ambiguities: {target_id}")
        if ambiguity_matches:
            row["classification"] = ambiguity_matches[0]
            tier_c.append(row)
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
    rule_paths = sorted(review_root.glob(RULE_GLOB))
    if not rule_paths:
        raise ValueError("missing bulk-family rule registry")
    # Load from the supplied review root rather than this module's source directory.
    old_tools = globals()["TOOLS"]
    try:
        globals()["TOOLS"] = review_root
        rules_doc, compiled = _load_rules()
    finally:
        globals()["TOOLS"] = old_tools
    audit = holds.audit(evidence_path, review_root=review_root,
                        registry_path=review_root / holds.REGISTRY.name)
    evidence, evidence_sha = cp._read(evidence_path)
    if evidence_sha != rules_doc.get("sourceEvidenceSha256"):
        raise ValueError("bulk-family rules target a different evidence snapshot")
    blocker_doc, _blocker_sha = cp._read(review_root / worklist.LEDGER.name)
    evidence_requirements = worklist.validate_ledger(
        blocker_doc, evidence, evidence_sha
    )
    reviews = resolver.load_reviews(review_root)
    held = {r["reviewTargetId"] for r in audit["heldTargets"]}

    # Validate every explicit bulk-family review row across all batches. A rule match
    # is never an approval without one of these destination-specific rows.
    reviewed_ids = set()
    coverage = []
    batch37_ids = set()
    batch38_ids = set()
    batch39_ids = set()
    batch40_ids = set()
    for path in sorted(review_root.glob("release_catalog_reviewed_nutrition_targets*.v1.json")):
        review_doc, _ = cp._read(path)
        for row in review_doc.get("items") or []:
            if "bulkFamilyRuleId" not in row:
                continue
            target_id = cp._text(row, "reviewTargetId", path.name)
            if target_id in reviewed_ids:
                raise ValueError(f"duplicate bulk-family target: {target_id}")
            matched = _matches(cp._text(row, "canonicalEnglishName", target_id), compiled)
            if len(matched) != 1:
                raise ValueError(f"bulk-family target must match exactly one rule: {target_id}")
            rule = matched[0]
            if row.get("bulkFamilyRuleId") != rule["ruleId"] or row.get("bulkFamilyTier") != rule["tier"]:
                raise ValueError(f"bulk-family rule receipt differs: {target_id}")
            if row.get("fdcId") != rule["fdcId"] or row.get("fdcDescription") != rule["fdcDescription"]:
                raise ValueError(f"bulk-family rule binding differs: {target_id}")
            if target_id in held:
                raise ValueError(f"held target cannot be bulk-reviewed: {target_id}")
            reviewed_ids.add(target_id)
            if path.name.startswith("release_catalog_reviewed_nutrition_targets_041"):
                batch37_ids.add(target_id)
            if path.name.startswith("release_catalog_reviewed_nutrition_targets_042"):
                batch38_ids.add(target_id)
            if path.name.startswith("release_catalog_reviewed_nutrition_targets_043"):
                batch39_ids.add(target_id)
            if path.name.startswith("release_catalog_reviewed_nutrition_targets_044"):
                batch40_ids.add(target_id)
            coverage.append({"reviewTargetId": target_id, "ruleId": rule["ruleId"], "tier": rule["tier"], "reviewFile": path.name})

    rule_covered_unreviewed, tier_b, tier_c = _partition_remaining(
        audit["remainingUnheldCandidates"],
        compiled,
        evidence_requirements=evidence_requirements,
        identity_ambiguities=(
            ("C-generic-pepper-identity-ambiguous", GENERIC_PEPPER),
            ("C-formulated-spice-blend-ambiguous", FORMULATED_SPICE_BLEND),
            ("C-formulated-herb-blend-ambiguous", FORMULATED_HERB_BLEND),
            ("C-formulated-pepper-salt-ambiguous", FORMULATED_PEPPER_SALT),
        ),
    )
    remaining_ids = {
        row["reviewTargetId"] for row in audit["remainingUnheldCandidates"]
    }
    active_requirements = {
        target_id: requirement
        for target_id, requirement in evidence_requirements.items()
        if target_id in remaining_ids
    }

    summary = {
        "recordedReviewTargetCount": audit["summary"]["recordedReviewTargetCount"],
        "heldReviewTargetCount": audit["summary"]["heldReviewTargetCount"],
        "remainingReviewTargetCount": len(audit["remainingUnheldCandidates"]),
        "explicitBulkReviewCount": len(reviewed_ids),
        "batch37ExplicitReviewCount": len(batch37_ids),
        "batch37TierACount": sum(r["tier"] == "A" and r["reviewTargetId"] in batch37_ids for r in coverage),
        "batch37TierBCount": sum(r["tier"] == "B" and r["reviewTargetId"] in batch37_ids for r in coverage),
        "batch38ExplicitReviewCount": len(batch38_ids),
        "batch38TierACount": sum(r["tier"] == "A" and r["reviewTargetId"] in batch38_ids for r in coverage),
        "batch38TierBCount": sum(r["tier"] == "B" and r["reviewTargetId"] in batch38_ids for r in coverage),
        "batch39ExplicitReviewCount": len(batch39_ids),
        "batch39TierACount": sum(r["tier"] == "A" and r["reviewTargetId"] in batch39_ids for r in coverage),
        "batch39TierBCount": sum(r["tier"] == "B" and r["reviewTargetId"] in batch39_ids for r in coverage),
        "batch40ExplicitReviewCount": len(batch40_ids),
        "batch40TierACount": sum(r["tier"] == "A" and r["reviewTargetId"] in batch40_ids for r in coverage),
        "batch40TierBCount": sum(r["tier"] == "B" and r["reviewTargetId"] in batch40_ids for r in coverage),
        "unreviewedRuleMatchCount": len(rule_covered_unreviewed),
        "activeEvidenceRequirementCount": len(active_requirements),
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
            "explicitEvidenceRequirementForcesContext": True,
            "networkRequestsPerformed": False,
        },
        "summary": summary,
        "bulkReviewCoverage": coverage,
        "batch37Coverage": [r for r in coverage if r["reviewTargetId"] in batch37_ids],
        "batch38Coverage": [r for r in coverage if r["reviewTargetId"] in batch38_ids],
        "batch39Coverage": [r for r in coverage if r["reviewTargetId"] in batch39_ids],
        "batch40Coverage": [r for r in coverage if r["reviewTargetId"] in batch40_ids],
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
