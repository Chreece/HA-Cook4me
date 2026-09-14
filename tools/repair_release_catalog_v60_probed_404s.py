#!/usr/bin/env python3
"""Repair one preserved v60 capture using targeted, fail-closed 404 evidence.

This tool never calls the provider. It accepts a previously captured catalog and
one read-only failed-detail probe artifact. A failed detail is reclassified as a
provider search row whose detail resource no longer exists only when all of the
following are true for the affected catalog:

* the current search-manifest count is unchanged from the capture,
* the number of currently absent IDs exactly equals the declared failures,
* every absent ID was independently probed,
* every probe reproduced pure HTTP 404, and
* none of those IDs is present in the captured recipe table.

If any condition differs, repair stops without writing a release candidate.
Nutrition, semantic identity, recipe grouping, and provider IDs are untouched.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

_DETAIL_NOT_FOUND_POLICY = "search-manifest-app-access-rcu-404-accounted-v1"
_EVIDENCE_KIND = "cook4me-v60-failed-detail-evidence"


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _save(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _variant_ids(catalog: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for group in catalog.get("recipes") or []:
        if not isinstance(group, dict):
            continue
        for variant in group.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            ident = _text(variant.get("variantId") or variant.get("searchVariantId"))
            if ident:
                out.add(ident)
    return out


def _catalog_key(row: dict[str, Any]) -> tuple[str, str]:
    language = _text(row.get("language")).lower()
    market = _text(row.get("market")).upper()
    if not market:
        country = _text(row.get("country")).upper()
        market = f"GS_{country}" if country else ""
    return language, market


def _capture_complete(payload: dict[str, Any]) -> bool:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    if int(source.get("unresolvedCanonicalIngredientNames") or 0):
        return False
    if int(source.get("unresolvedCanonicalRecipeNames") or 0):
        return False
    if int(source.get("failedDetailCount") or 0):
        return False

    catalogs = source.get("catalogs") if isinstance(source.get("catalogs"), list) else []
    if len(catalogs) != int(source.get("auditedCatalogCount") or 0):
        return False
    for row in catalogs:
        if not isinstance(row, dict):
            return False
        unique = int(row.get("uniqueVariants") or 0)
        hydrated = int(row.get("hydratedVariants") or 0)
        failed = int(row.get("failedDetails") or 0)
        not_found = int(row.get("detailNotFoundCount") or 0)
        if failed or min(unique, hydrated, not_found) < 0:
            return False
        if hydrated + not_found != unique:
            return False

    if source.get("nutritionRequiredForComplete") is not False:
        return False
    return True


def repair(
    catalog: dict[str, Any],
    evidence: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if evidence.get("kind") != _EVIDENCE_KIND:
        raise RuntimeError("unexpected failed-detail evidence kind")
    if _text(evidence.get("catalogVersion")) != _text(catalog.get("catalogVersion")):
        raise RuntimeError("failed-detail evidence catalogVersion does not match capture")
    policy = evidence.get("policy") if isinstance(evidence.get("policy"), dict) else {}
    if policy.get("readOnly") is not True or policy.get("providerVariantIdentityInferred") is not False:
        raise RuntimeError("failed-detail evidence policy is not fail-closed")
    if evidence.get("secretsPersisted") is not False:
        raise RuntimeError("failed-detail evidence reports persisted secrets")

    result = deepcopy(catalog)
    source = result.get("source") if isinstance(result.get("source"), dict) else None
    if source is None:
        raise RuntimeError("catalog source metadata is missing")
    source_rows = source.get("catalogs") if isinstance(source.get("catalogs"), list) else None
    if source_rows is None:
        raise RuntimeError("catalog source.catalogs is missing")

    captured_ids = _variant_ids(result)
    source_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    declared_failed_total = 0
    for row in source_rows:
        if not isinstance(row, dict):
            raise RuntimeError("catalog source.catalogs contains a non-object row")
        key = _catalog_key(row)
        if not all(key):
            raise RuntimeError("catalog source row has incomplete language/market identity")
        if key in source_by_key:
            raise RuntimeError(f"duplicate catalog source identity: {key}")
        source_by_key[key] = row
        declared_failed_total += int(row.get("failedDetails") or 0)

    evidence_rows = evidence.get("catalogs") if isinstance(evidence.get("catalogs"), list) else []
    evidence_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    all_not_found_ids: set[str] = set()
    repaired_total = 0

    for raw in evidence_rows:
        if not isinstance(raw, dict):
            raise RuntimeError("failed-detail evidence contains a non-object catalog row")
        key = _catalog_key(raw)
        if key in evidence_by_key:
            raise RuntimeError(f"duplicate failed-detail evidence identity: {key}")
        evidence_by_key[key] = raw

        source_row = source_by_key.get(key)
        if source_row is None:
            raise RuntimeError(f"failed-detail evidence references unknown catalog: {key}")

        declared_unique = int(raw.get("declaredUniqueVariants") or 0)
        declared_hydrated = int(raw.get("declaredHydratedVariants") or 0)
        declared_failed = int(raw.get("declaredFailedDetails") or 0)
        current_search = int(raw.get("currentSearchCount") or 0)
        current_candidates = int(raw.get("currentCandidateCount") or 0)
        probed = int(raw.get("probedCount") or 0)
        present = int(raw.get("presentInCapturedCatalogCount") or 0)
        unattributed = int(raw.get("unattributedDeclaredFailureCount") or 0)

        if declared_failed <= 0:
            raise RuntimeError(f"evidence row {key} does not describe a failure")
        if raw.get("state") != "probed":
            raise RuntimeError(f"evidence row {key} was not fully probed")
        if raw.get("searchManifestCountStable") is not True:
            raise RuntimeError(f"search manifest drift detected for {key}")
        if raw.get("candidateCountMatchesDeclaredFailures") is not True:
            raise RuntimeError(f"candidate/failure count mismatch for {key}")
        if unattributed:
            raise RuntimeError(f"unattributed historical failures remain for {key}")
        if not (
            current_search == declared_unique
            and current_candidates == declared_failed
            and probed == declared_failed
            and present == declared_hydrated
            and declared_hydrated + declared_failed == declared_unique
        ):
            raise RuntimeError(f"failed-detail count reconciliation failed for {key}")

        if int(source_row.get("uniqueVariants") or 0) != declared_unique:
            raise RuntimeError(f"capture/evidence uniqueVariants mismatch for {key}")
        if int(source_row.get("hydratedVariants") or 0) != declared_hydrated:
            raise RuntimeError(f"capture/evidence hydratedVariants mismatch for {key}")
        if int(source_row.get("failedDetails") or 0) != declared_failed:
            raise RuntimeError(f"capture/evidence failedDetails mismatch for {key}")

        outcomes = raw.get("outcomes") if isinstance(raw.get("outcomes"), dict) else {}
        if outcomes != {"http-404": declared_failed}:
            raise RuntimeError(f"non-404 failed-detail outcome detected for {key}: {outcomes}")

        rows = raw.get("evidence") if isinstance(raw.get("evidence"), list) else []
        if len(rows) != declared_failed:
            raise RuntimeError(f"failed-detail evidence row count mismatch for {key}")
        ids: list[str] = []
        for item in rows:
            if not isinstance(item, dict) or item.get("outcome") != "http-404":
                raise RuntimeError(f"non-404 detail evidence item detected for {key}")
            ident = _text(item.get("variantId"))
            if not ident:
                raise RuntimeError(f"empty provider variant ID in failed-detail evidence for {key}")
            ids.append(ident)
        if len(ids) != len(set(ids)):
            raise RuntimeError(f"duplicate provider variant IDs in failed-detail evidence for {key}")
        if any(ident in captured_ids for ident in ids):
            raise RuntimeError(f"404 provider identity is already present in captured recipes for {key}")
        overlap = all_not_found_ids.intersection(ids)
        if overlap:
            raise RuntimeError(f"404 provider identity appears in multiple catalogs: {sorted(overlap)[:5]}")
        all_not_found_ids.update(ids)

        source_row["failedDetails"] = 0
        source_row["detailNotFoundCount"] = len(ids)
        source_row["detailNotFoundVariantIds"] = sorted(ids)
        repaired_total += len(ids)

    failed_keys = {
        key for key, row in source_by_key.items() if int(row.get("failedDetails") or 0) > 0
    }
    if failed_keys:
        raise RuntimeError(f"failed catalogs remain without accepted probe evidence: {sorted(failed_keys)}")

    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    if int(summary.get("declaredFailedDetailCount") or 0) != declared_failed_total:
        raise RuntimeError("probe summary declared-failure count does not match capture")
    if int(summary.get("currentCandidateCount") or 0) != repaired_total:
        raise RuntimeError("probe summary candidate count does not match repaired count")
    if int(summary.get("probedCount") or 0) != repaired_total:
        raise RuntimeError("probe summary probed count does not match repaired count")
    if int(summary.get("searchFailureCount") or 0):
        raise RuntimeError("probe contained search failures")
    if summary.get("outcomes") != {"http-404": repaired_total}:
        raise RuntimeError("probe summary contains a non-404 outcome")

    source["failedDetailCount"] = 0
    source["detailNotFoundCount"] = repaired_total
    source["detailNotFoundPolicy"] = _DETAIL_NOT_FOUND_POLICY
    source["detailNotFoundVariantIdsStored"] = True
    source["detailNotFoundEvidence"] = "stable-manifest-targeted-reprobe-http404-v1"
    source["detailNotFoundEvidenceCount"] = repaired_total
    source["detailNotFoundProviderIdentityInferred"] = False
    result["complete"] = _capture_complete(result)
    if result["complete"] is not True:
        raise RuntimeError("repaired catalog is still not capture-complete")

    repair_summary = {
        "catalogVersion": _text(result.get("catalogVersion")),
        "repairedDetailNotFoundCount": repaired_total,
        "affectedCatalogCount": len(evidence_rows),
        "capturedVariantCount": len(captured_ids),
        "catalogComplete": True,
        "providerVariantIdentityInferred": False,
        "networkRequestsPerformed": False,
        "secretsPersisted": False,
    }
    return result, repair_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()

    catalog_path = Path(args.catalog).expanduser()
    evidence_path = Path(args.evidence).expanduser()
    output_path = Path(args.output).expanduser()
    summary_path = Path(args.summary).expanduser()

    repaired, summary = repair(_load(catalog_path), _load(evidence_path))
    _save(output_path, repaired)
    summary.update(
        {
            "inputCatalogSha256": _sha256(catalog_path),
            "evidenceSha256": _sha256(evidence_path),
            "outputCatalogSha256": _sha256(output_path),
            "outputBytes": output_path.stat().st_size,
        }
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
