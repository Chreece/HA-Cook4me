#!/usr/bin/env python3
"""Reconcile a preserved v60 capture with exact public 404 probe evidence."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import build_release_catalog_v60_reviewed as reviewed
import release_catalog_detail_not_found_v60 as detail_not_found

EVIDENCE_KIND = "cook4me-v60-failed-detail-evidence"


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def reconcile(catalog: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    if evidence.get("kind") != EVIDENCE_KIND:
        raise RuntimeError("invalid failed-detail evidence kind")
    if _text(evidence.get("catalogVersion")) != _text(catalog.get("catalogVersion")):
        raise RuntimeError("failed-detail evidence catalog version mismatch")

    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    if int(summary.get("searchFailureCount") or 0):
        raise RuntimeError("failed-detail evidence contains search failures")
    declared_total = int(summary.get("declaredFailedDetailCount") or 0)
    candidate_total = int(summary.get("currentCandidateCount") or 0)
    probed_total = int(summary.get("probedCount") or 0)
    outcomes = summary.get("outcomes") if isinstance(summary.get("outcomes"), dict) else {}
    if not declared_total or candidate_total != declared_total or probed_total != declared_total:
        raise RuntimeError("failed-detail evidence totals do not exactly reconcile")
    if outcomes != {"http-404": declared_total}:
        raise RuntimeError("failed-detail evidence is not exclusively HTTP 404")

    result = deepcopy(catalog)
    source = result.get("source") if isinstance(result.get("source"), dict) else None
    if source is None:
        raise RuntimeError("catalog source metadata is missing")
    if int(source.get("failedDetailCount") or 0) != declared_total:
        raise RuntimeError("catalog failedDetailCount does not match evidence")
    catalog_rows = source.get("catalogs") if isinstance(source.get("catalogs"), list) else []
    rows_by_key = {
        (_text(row.get("language")).lower(), _text(row.get("country")).upper()): row
        for row in catalog_rows
        if isinstance(row, dict)
    }

    reconciled = 0
    for row in evidence.get("catalogs") or []:
        if not isinstance(row, dict):
            raise RuntimeError("failed-detail evidence contains a non-object catalog row")
        if row.get("state") != "probed":
            raise RuntimeError("failed-detail evidence catalog row was not probed")
        if row.get("searchManifestCountStable") is not True:
            raise RuntimeError("failed-detail search manifest is not stable")
        if row.get("candidateCountMatchesDeclaredFailures") is not True:
            raise RuntimeError("failed-detail candidate count does not match capture failures")
        if int(row.get("unattributedDeclaredFailureCount") or 0):
            raise RuntimeError("failed-detail evidence leaves unattributed failures")

        language = _text(row.get("language")).lower()
        country = _text(row.get("country")).upper()
        target = rows_by_key.get((language, country))
        if target is None:
            raise RuntimeError(f"catalog row {language}/{country} is missing")
        declared = int(row.get("declaredFailedDetails") or 0)
        if int(target.get("failedDetails") or 0) != declared:
            raise RuntimeError(f"catalog row {language}/{country} failure count drifted")
        if int(target.get("uniqueVariants") or 0) != int(row.get("declaredUniqueVariants") or 0):
            raise RuntimeError(f"catalog row {language}/{country} unique count drifted")
        if int(target.get("hydratedVariants") or 0) != int(row.get("declaredHydratedVariants") or 0):
            raise RuntimeError(f"catalog row {language}/{country} hydrated count drifted")

        evidence_rows = row.get("evidence") if isinstance(row.get("evidence"), list) else []
        ids = sorted(
            _text(item.get("variantId"))
            for item in evidence_rows
            if isinstance(item, dict)
        )
        if len(ids) != declared or any(not ident for ident in ids) or ids != sorted(set(ids)):
            raise RuntimeError(f"catalog row {language}/{country} evidence IDs do not reconcile")
        for item in evidence_rows:
            if not isinstance(item, dict):
                raise RuntimeError("failed-detail evidence contains a non-object probe row")
            if item.get("outcome") != "http-404" or item.get("httpStatuses") != [404]:
                raise RuntimeError(f"catalog row {language}/{country} contains non-404 evidence")

        target["failedDetails"] = 0
        target["detailNotFoundCount"] = declared
        target["detailNotFoundVariantIds"] = ids
        reconciled += declared

    if reconciled != declared_total:
        raise RuntimeError("reconciled detail count does not match evidence total")

    source["failedDetailCount"] = sum(
        int(row.get("failedDetails") or 0) for row in catalog_rows if isinstance(row, dict)
    )
    source["detailNotFoundCount"] = sum(
        int(row.get("detailNotFoundCount") or 0) for row in catalog_rows if isinstance(row, dict)
    )
    source["detailNotFoundPolicy"] = detail_not_found._CURRENT_PROBE_POLICY
    source["detailNotFoundVariantIdsStored"] = True
    source["detailNotFoundEvidenceKind"] = detail_not_found._CURRENT_PROBE_EVIDENCE_KIND
    source["detailNotFoundEvidenceGeneratedAt"] = _text(evidence.get("generatedAt"))
    source["detailNotFoundEvidenceCount"] = reconciled
    source["detailNotFoundSearchManifestStable"] = True
    source["detailNotFoundCandidateCountMatched"] = True
    source["detailNotFoundPublicApp404Only"] = True
    result["complete"] = reviewed._capture_complete(result)

    errors = detail_not_found.validation_errors(result)
    if errors:
        raise RuntimeError("reconciled detail accounting is invalid: " + "; ".join(errors))
    if result.get("complete") is not True:
        raise RuntimeError("reconciled catalog is still not capture-complete")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = reconcile(_load(Path(args.catalog)), _load(Path(args.evidence)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    source = result.get("source") or {}
    print(json.dumps({
        "complete": result.get("complete") is True,
        "failedDetailCount": int(source.get("failedDetailCount") or 0),
        "detailNotFoundCount": int(source.get("detailNotFoundCount") or 0),
        "output": str(output),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
