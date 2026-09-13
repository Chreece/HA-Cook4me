#!/usr/bin/env python3
"""Trace unresolved nutrition targets to exact reviewed labels and saved recipe lines.

Offline evidence extraction only: no nutrient selection, semantic correction,
provider identity inference, unit conversion, or source mutation is performed.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import gzip
import json
import math
from pathlib import Path
from typing import Any
import sys

import compile_release_catalog_semantics_v60 as semantics
import nutrition_review_holds_v60 as holds
import prepare_nutrition_review_worklist_v60 as worklist
import snapshot_nutrition_review_checkpoint_v60 as checkpoint

TOOLS = Path(__file__).resolve().parent
FINDINGS = TOOLS / "release_catalog_nutrition_context_findings.v1.json"
PROVIDER_REVIEW = "release_catalog_reviewed_provider_food_english.v2.json"
MAX_CAPTURE_BYTES = 256 * 1024 * 1024
POLICY = {
    "bindingsApproved": False, "sourceCorrectionsApplied": False,
    "providerIdentityInference": False, "sameNameJoinPerformed": False,
    "massBasisInferred": False, "unitConversionPerformed": False,
    "networkRequestsPerformed": False, "sourceFilesModified": False,
}


def _list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context}: expected a list")
    return value


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{context}: expected an object")
    return value


def _read_sources(root: Path) -> tuple[list[tuple[str, dict[str, Any]]], list[dict[str, str]]]:
    paths = semantics._review_paths(root)
    if not paths:
        raise ValueError("no semantic source review files")
    payloads, fingerprints = [], []
    for path in paths:
        value, digest = checkpoint._read(path)
        if value.get("kind") != "cook4me-reviewed-keyless-ingredient-semantics":
            raise ValueError(f"invalid semantic source file: {path.name}")
        # The legacy compiler skips malformed rows. This evidence export must not.
        for raw in _list(value.get("items"), path.name):
            raw = _object(raw, path.name)
            for key in ("language", "source", "english", "classification"):
                if not isinstance(raw.get(key), str) or not raw[key].strip():
                    raise ValueError(f"{path.name}: invalid source {key}")
            if semantics._text(raw["classification"]).lower() not in semantics._ALLOWED_CLASSIFICATIONS:
                raise ValueError(f"{path.name}: invalid source classification")
            if "confidence" in raw and not isinstance(raw["confidence"], str):
                raise ValueError(f"{path.name}: invalid source confidence")
        payloads.append((path.name, value))
        fingerprints.append({"path": path.name, "sha256": digest})
    return payloads, fingerprints


def collect_context(requirements: dict[str, dict[str, Any]], evidence: dict[str, Any],
                    review_root: Path = TOOLS) -> dict[str, Any]:
    """Join a concept only through the established compiler's full source IDs."""
    payloads, fingerprints = _read_sources(review_root)
    compiled = semantics.compile_semantic_concepts(payloads)
    concepts = {r["conceptId"]: r for r in compiled["concepts"]}
    originals = {r["reviewTargetId"]: r for r in evidence["items"]}
    file_hashes = {r["path"]: r["sha256"] for r in fingerprints}
    raw_index: dict[tuple[str, str, str], tuple[int, dict[str, Any]]] = {}
    for name, value in payloads:
        for index, row in enumerate(value["items"]):
            key = (name, semantics._text(row["language"]).lower(), semantics._norm(row["source"]))
            raw_index.setdefault(key, (index, row))
    provider, provider_sha = checkpoint._read(review_root / PROVIDER_REVIEW)
    if (provider.get("kind") != "cook4me-reviewed-provider-food-english"
            or not isinstance(provider.get("items"), dict)):
        raise ValueError("invalid exact-key provider review source")
    fingerprints.append({"path": PROVIDER_REVIEW, "sha256": provider_sha})
    targets = []
    for target_id, requirement in requirements.items():
        row = originals[target_id]
        target = {k: deepcopy(row[k]) for k in ("reviewTargetId", "reviewTargetKind", "canonicalEnglishName", "memberCount", "usageCountSum")}
        target.update({"sourceTargetSha256": checkpoint._digest(checkpoint._encoded(row)),
                       "evidenceRequired": requirement["evidenceRequired"], "sourceLabels": [],
                       "nutritionApprovalGranted": False, "measurementBasisEstablished": False})
        if row["reviewTargetKind"] == "semantic-concept":
            concept = concepts.get(target_id)
            if (concept is None or concept["classification"] != "food"
                    or concept["mergePolicy"] != "reviewed-high-exact-english"
                    or semantics._norm(concept["canonicalEnglish"]) != semantics._norm(row["canonicalEnglishName"])):
                raise ValueError(f"exact semantic concept missing or changed: {target_id}")
            members = concept["sourceIdentities"]
            if type(row["memberCount"]) is not int or len(members) != row["memberCount"]:
                raise ValueError(f"semantic member count differs from frozen snapshot: {target_id}")
            for member in members:
                local_id = member["ingredientId"]
                if (semantics.source_local_ingredient_id(member["language"], member["source"]) != local_id
                        or compiled["sourceIdentityToConcept"].get(local_id) != target_id):
                    raise ValueError(f"unproven source membership: {local_id}")
                item_index, raw = raw_index[(member["reviewFile"], member["language"], semantics._norm(member["source"]))]
                target["sourceLabels"].append({
                    "ingredientId": local_id, "language": member["language"],
                    "source": member["source"], "reviewedEnglish": raw["english"],
                    "reviewFile": member["reviewFile"], "reviewFileSha256": file_hashes[member["reviewFile"]],
                    "reviewItemIndex": item_index, "reviewItemSha256": checkpoint._digest(checkpoint._encoded(raw)),
                    "confidence": member["confidence"],
                })
            target["memberIngredientIds"] = sorted(m["ingredientId"] for m in members)
            target["contextStatus"] = "reviewed-source-labels-only-not-measurement-context"
        else:
            if row["memberCount"] != 1 or type(row["memberCount"]) is not int:
                raise ValueError(f"provider target must be one exact identity: {target_id}")
            target["memberIngredientIds"] = [target_id]
            raw = provider["items"].get(target_id)
            if raw is None:
                target["contextStatus"] = "exact-provider-review-not-retained"
            else:
                raw = _object(raw, target_id)
                english = checkpoint._text(raw, "english", target_id)
                if semantics._norm(english) != semantics._norm(row["canonicalEnglishName"]):
                    raise ValueError(f"provider canonical evidence differs: {target_id}")
                target["providerReview"] = {"providerIngredientId": target_id, "english": english,
                    "reviewFile": PROVIDER_REVIEW, "reviewFileSha256": provider_sha,
                    "reviewItemSha256": checkpoint._digest(checkpoint._encoded(raw))}
                target["contextStatus"] = "exact-provider-review-only-not-measurement-context"
        targets.append(target)
    return {"targets": targets, "sourceFiles": fingerprints,
            "sourceFilesSha256": checkpoint._digest(checkpoint._encoded(fingerprints))}


def validate_findings(value: dict[str, Any], context: dict[str, Any], evidence_sha: str) -> list[dict[str, Any]]:
    """Check explicitly written findings against exact retained source rows."""
    if (type(value.get("schemaVersion")) is not int or value["schemaVersion"] != 1
            or value.get("kind") != "cook4me-nutrition-source-context-findings-v60"
            or value.get("sourceEvidenceSha256") != evidence_sha
            or not isinstance(value.get("policy"), dict)
            or any(value["policy"].get(k) is not v for k, v in POLICY.items())):
        raise ValueError("invalid source-context findings header/policy")
    targets = {r["reviewTargetId"]: r for r in context["targets"]}
    output, seen = [], set()
    for raw in _list(value.get("items"), "findings"):
        raw = _object(raw, "finding")
        ident = checkpoint._text(raw, "findingId", "finding")
        if ident in seen:
            raise ValueError("duplicate context finding ID")
        seen.add(ident)
        if raw.get("status") != "unresolved-source-semantics" or any(k in raw for k in ("fdcId", "selectedFdcId", "replacementFdcId")):
            raise ValueError("a context finding cannot approve a binding")
        for key in ("observedPreparationEnglish", "reason", "evidenceRequired"):
            checkpoint._text(raw, key, ident)
        target = targets.get(raw.get("reviewTargetId"))
        source = next((r for r in (target or {}).get("sourceLabels", []) if r["ingredientId"] == raw.get("ingredientId")), None)
        keys = ("ingredientId", "language", "source", "reviewedEnglish", "reviewFile", "reviewFileSha256", "reviewItemIndex", "reviewItemSha256")
        if source is None or any(raw.get(k) != source.get(k) for k in keys):
            raise ValueError(f"context finding source provenance differs: {ident}")
        output.append(deepcopy(raw))
    return output


def _capture(path: Path) -> tuple[dict[str, Any], str, str]:
    """Bound both compressed and decompressed input; reject duplicate JSON keys."""
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_CAPTURE_BYTES:
        raise ValueError("capture must be a regular file within the 256 MiB limit")
    raw = path.read_bytes()
    if path.suffix == ".gz":
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            decoded = stream.read(MAX_CAPTURE_BYTES + 1)
    else:
        decoded = raw
    if len(decoded) > MAX_CAPTURE_BYTES:
        raise ValueError("decoded capture exceeds the 256 MiB limit")
    value = json.loads(decoded.decode("utf-8"), object_pairs_hook=checkpoint._pairs, parse_constant=checkpoint._constant)
    return _object(value, "capture"), checkpoint._digest(raw), checkpoint._digest(decoded)


def _projection(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in fields:
        if key not in row:
            continue
        value = row[key]
        if value is not None and (type(value) not in (str, int, float) or isinstance(value, float) and not math.isfinite(value)):
            raise ValueError(f"capture {key}: expected a finite scalar or null")
        if isinstance(value, str) and len(value) > 4096:
            raise ValueError(f"capture {key}: unexpected oversized value")
        out[key] = value
    return out


def extract_capture_context(payload: dict[str, Any], context: dict[str, Any], catalog_version: str) -> dict[str, Any]:
    """Copy allowlisted evidence from a normalized saved catalog; never join by name."""
    if (type(payload.get("schemaVersion")) is not int or payload["schemaVersion"] != 1
            or payload.get("catalogVersion") != catalog_version):
        raise ValueError("expected the matching schema-1 v60 capture catalog")
    globals_ = _list(payload.get("ingredients"), "capture ingredients")
    recipes = _list(payload.get("recipes"), "capture recipes")
    by_member = {}
    for target in context["targets"]:
        for ident in target["memberIngredientIds"]:
            if ident in by_member:
                raise ValueError("ingredient identity belongs to multiple context targets")
            by_member[ident] = target
    results = {r["reviewTargetId"]: {"reviewTargetId": r["reviewTargetId"], "globalRows": [], "recipeLines": []} for r in context["targets"]}
    aliases = ("id", "ingredientId", "key", "foodKey", "providerIngredientId", "providerFoodKey")

    def matched(row: dict[str, Any], *, line: bool) -> tuple[str, dict[str, Any]] | None:
        identifiers = {row[k] for k in aliases if isinstance(row.get(k), str) and row[k]}
        matches = identifiers & by_member.keys()
        if not matches:
            return None  # A matching label or conceptId alone is never identity proof.
        if any(row.get(k) is not None and not isinstance(row[k], str) for k in aliases if k in row):
            raise ValueError("invalid capture identity field type")
        if len(matches) != 1 or len(identifiers) != 1:
            raise ValueError("conflicting exact ingredient identity fields in capture")
        ident = next(iter(matches))
        target = by_member[ident]
        if target["reviewTargetKind"] == "provider-identity":
            explicit = {row[k] for k in aliases[2:] if isinstance(row.get(k), str) and row[k]}
            if explicit != {ident} or row.get("sourceLocalIdentity") is True:
                raise ValueError(f"provider context lacks explicit key: {ident}")
        elif any(row.get(k) not in (None, "") for k in aliases[2:]):
            raise ValueError(f"local context cannot assign a provider key: {ident}")
        elif line:
            source = checkpoint._text(row, "semanticSourceName", ident)
            language = checkpoint._text(row, "originalLanguage", ident)
            if semantics.source_local_ingredient_id(language, source) != ident:
                raise ValueError(f"captured source-local label/identity mismatch: {ident}")
        if target["reviewTargetKind"] == "semantic-concept" and row.get("conceptId") not in (None, "", target["reviewTargetId"]):
            raise ValueError(f"captured concept membership differs: {ident}")
        return ident, target

    seen_globals: set[str] = set()
    for i, raw in enumerate(globals_):
        row = _object(raw, "capture global ingredient")
        match = matched(row, line=False)
        if not match:
            continue
        ident, target = match
        if ident in seen_globals:
            raise ValueError("duplicate target ingredient in capture globals")
        seen_globals.add(ident)
        results[target["reviewTargetId"]]["globalRows"].append({"ingredientId": ident, "globalRowIndex": i,
            "sourceRowSha256": checkpoint._digest(checkpoint._encoded(row)),
            "fields": _projection(row, ("canonicalName", "originalName", "originalLanguage", "semanticSourceName", "conceptId"))})
    for gi, group in enumerate(recipes):
        group = _object(group, "capture recipe")
        for vi, variant in enumerate(_list(group.get("variants"), "capture variants")):
            variant = _object(variant, "capture variant")
            for li, raw in enumerate(_list(variant.get("ingredients"), "capture recipe ingredients")):
                row = _object(raw, "capture recipe line")
                match = matched(row, line=True)
                if not match:
                    continue
                ident, target = match
                if ident not in seen_globals:
                    raise ValueError(f"target recipe line has no exact global ingredient: {ident}")
                results[target["reviewTargetId"]]["recipeLines"].append({
                    "ingredientId": ident, "recipeIndex": gi, "variantIndex": vi, "lineIndex": li,
                    "recipeIdentity": _projection(group, ("groupingFunctionalId",)),
                    "variantIdentity": _projection(variant, ("variantId", "searchVariantId", "originalLanguage")),
                    "sourceRowSha256": checkpoint._digest(checkpoint._encoded(row)),
                    "fields": _projection(row, ("originalName", "originalLanguage", "semanticSourceName", "quantity", "unit", "unitKey")),
                })
    rows = list(results.values())
    for row in rows:
        row["status"] = "exact-recipe-lines-retained-not-interpreted" if row["recipeLines"] else "no-exact-recipe-lines-in-supplied-capture"
        row["massBasisInferred"] = False
    return {"kind": "cook4me-exact-target-capture-context-v60", "policy": dict(POLICY), "targets": rows,
            "summary": {"targetsWithRecipeLines": sum(bool(r["recipeLines"]) for r in rows),
                        "recipeLineCount": sum(len(r["recipeLines"]) for r in rows)},
            "captureCompletenessCertified": False, "unknownFieldsCopied": False}


def build_outputs(evidence_path: Path, *, review_root: Path = TOOLS,
                  capture_path: Path | None = None) -> dict[str, Any]:
    audit = holds.audit(evidence_path, review_root=review_root, registry_path=review_root / holds.REGISTRY.name)
    evidence, evidence_sha = checkpoint._read(evidence_path)
    if evidence_sha != audit["evidenceSha256"]:
        raise ValueError("evidence changed during audit")
    ledger_path = review_root / worklist.LEDGER.name
    ledger, ledger_sha = checkpoint._read(ledger_path)
    requirements = worklist.validate_ledger(ledger, evidence, evidence_sha)
    context = collect_context(requirements, evidence, review_root)
    findings_path = review_root / FINDINGS.name
    findings_value, findings_sha = checkpoint._read(findings_path)
    findings = validate_findings(findings_value, context, evidence_sha)
    baseline = checkpoint.build_checkpoint(review_root)
    if baseline["reviewFilesSha256"] != audit["reviewFilesSha256"]:
        raise ValueError("nutrition reviews changed during audit")
    recorded = {r["reviewTargetId"]: r for r in baseline["recordedBindings"]}
    annotated, _untriaged = worklist.partition_requirements(requirements, audit["remainingUnheldCandidates"], recorded,
                                                          {r["reviewTargetId"] for r in audit["heldTargets"]})
    statuses = {r["reviewTargetId"]: r["currentStatus"] for r in annotated}
    for target in context["targets"]:
        target["currentReviewStatus"] = statuses[target["reviewTargetId"]]
    summary = {**audit["summary"], "contextRequirementCount": len(requirements),
               "semanticTargetsWithSourceLabels": sum(bool(r["sourceLabels"]) for r in context["targets"]),
               "reviewedSourceLabelCount": sum(len(r["sourceLabels"]) for r in context["targets"]),
               "providerTargetsWithoutExactReview": sum(r["contextStatus"] == "exact-provider-review-not-retained" for r in context["targets"]),
               "documentedSourceContextFindingCount": len(findings), "newBindingsApproved": 0,
               "captureSupplied": capture_path is not None}
    report = {"schemaVersion": 1, "kind": "cook4me-nutrition-target-source-context-v60", "policy": dict(POLICY),
              "catalogVersion": evidence["catalogVersion"], "sourceEvidenceSha256": evidence_sha,
              "referenceManifestSha256": evidence["referenceManifestSha256"],
              "reviewFilesSha256": baseline["reviewFilesSha256"], "holdRegistrySha256": audit["registrySha256"],
              "requirementLedgerSha256": ledger_sha, "findingsFileSha256": findings_sha,
              "readyForManualReview": audit["readyForManualReview"], "catalogNutritionApprovalGranted": False,
              "summary": summary, "findings": findings, **context}
    outputs = {"context.json": report, "summary.json": summary, "hold-audit.json": audit}
    if capture_path is not None:
        payload, capture_sha, decoded_sha = _capture(capture_path)
        capture = extract_capture_context(payload, context, evidence["catalogVersion"])
        capture.update({"captureFileSha256": capture_sha, "decodedCaptureSha256": decoded_sha,
                        "sourceEvidenceSha256": evidence_sha, "catalogVersion": evidence["catalogVersion"]})
        outputs["capture-context.json"] = capture
        summary.update(capture["summary"])
        if checkpoint._digest(capture_path.read_bytes()) != capture_sha:
            raise ValueError("capture changed during extraction")
    # Reject source drift instead of publishing a mixed-time evidence receipt.
    if [p.name for p in semantics._review_paths(review_root)] != [r["path"] for r in context["sourceFiles"] if r["path"] != PROVIDER_REVIEW]:
        raise ValueError("semantic source file set changed during extraction")
    for row in [*context["sourceFiles"], {"path": ledger_path.name, "sha256": ledger_sha},
                {"path": findings_path.name, "sha256": findings_sha}]:
        _, actual = checkpoint._read(review_root / row["path"])
        if actual != row["sha256"]:
            raise ValueError(f"source file changed during extraction: {row['path']}")
    if (checkpoint._read(evidence_path)[1] != evidence_sha
            or checkpoint._read(review_root / holds.REGISTRY.name)[1] != audit["registrySha256"]
            or checkpoint.build_checkpoint(review_root)["reviewFilesSha256"] != baseline["reviewFilesSha256"]):
        raise ValueError("evidence, hold registry or nutrition reviews changed during extraction")
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True, help="Existing full pinned offline candidate JSON")
    parser.add_argument("--capture", type=Path, help="Optional existing normalized v60 capture3 catalog JSON or JSON.gz")
    parser.add_argument("--output", type=Path, required=True, help="New output directory, never overwritten")
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("output directory must not exist")
        outputs = build_outputs(args.evidence, capture_path=args.capture)
        args.output.mkdir(parents=True, exist_ok=False)
        for name, value in outputs.items():
            (args.output / name).write_bytes(checkpoint._encoded(value))
        print(json.dumps(outputs["summary.json"], sort_keys=True))
        summary = outputs["summary.json"]
        return 2 if (summary["remainingEvidenceTargetCount"] or summary["heldReviewTargetCount"]
                     or summary["unheldProvenanceMismatchCount"] or summary["documentedSourceContextFindingCount"]) else 0
    except (OSError, EOFError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
