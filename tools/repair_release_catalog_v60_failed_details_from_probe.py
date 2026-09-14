#!/usr/bin/env python3
"""Repair a preserved v60 capture using exact failed-detail probe evidence.

This is deliberately fail-closed. It never invents recipe content and never
removes a successfully hydrated recipe. A failed provider search row is moved
from ``failedDetails`` to explicit ``detailNotFound`` accounting only when a
separate current-state probe proves all of the following:

* the catalog manifest count is stable;
* the current missing-ID count exactly equals the captured failed-detail count;
* every missing exact provider variant ID was probed;
* every probe result is pure HTTP 404; and
* none of those IDs is present in the captured recipe table.

The repaired catalog remains the same recipe/ingredient payload. Only capture
accounting and the capture-complete flag change.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog_v60_reviewed as reviewed  # type: ignore  # noqa: E402
import release_catalog_detail_not_found_v60 as detail_not_found  # type: ignore  # noqa: E402


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


def _captured_variant_ids(payload: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for group in payload.get("recipes") or []:
        if not isinstance(group, dict):
            continue
        for variant in group.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            ident = _text(variant.get("variantId") or variant.get("searchVariantId"))
            if ident:
                out.add(ident)
    return out


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def repair(
    catalog: dict[str, Any], evidence: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = deepcopy(catalog)
    _require(
        evidence.get("kind") == "cook4me-v60-failed-detail-evidence",
        "unexpected failed-detail evidence kind",
    )
    _require(
        _text(evidence.get("catalogVersion")) == _text(result.get("catalogVersion")),
        "failed-detail evidence catalogVersion does not match captured catalog",
    )
    policy = evidence.get("policy") if isinstance(evidence.get("policy"), dict) else {}
    _require(policy.get("providerVariantIdentityPreserved") is True, "probe did not preserve provider identity")
    _require(policy.get("providerVariantIdentityInferred") is False, "probe inferred provider identity")
    _require(policy.get("rawExceptionsPersisted") is False, "probe persisted raw exceptions")
    _require(evidence.get("secretsPersisted") is False, "probe evidence persisted secrets")

    summary = evidence.get("summary") if isinstance(evidence.get("summary"), dict) else {}
    declared = int(summary.get("declaredFailedDetailCount") or 0)
    current = int(summary.get("currentCandidateCount") or 0)
    probed = int(summary.get("probedCount") or 0)
    _require(declared > 0, "probe contains no failed detail rows")
    _require(declared == current == probed, "probe count reconciliation is not exact")
    _require(int(summary.get("searchFailureCount") or 0) == 0, "one or more failed catalog manifests could not be reprobed")
    _require(summary.get("outcomes") == {"http-404": probed}, "probe contains a non-404 outcome")

    source = result.get("source") if isinstance(result.get("source"), dict) else None
    _require(source is not None, "captured catalog has no source metadata")
    catalogs = source.get("catalogs") if isinstance(source.get("catalogs"), list) else None
    _require(catalogs is not None, "captured catalog has no source.catalogs list")
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    for row in catalogs:
        if not isinstance(row, dict):
            continue
        key = (_text(row.get("language")).lower(), _text(row.get("country")).upper())
        _require(key not in rows, f"duplicate source catalog identity: {key}")
        rows[key] = row

    captured_ids = _captured_variant_ids(result)
    repaired_ids: set[str] = set()
    repaired_catalogs = 0
    repaired_count = 0

    evidence_rows = evidence.get("catalogs") if isinstance(evidence.get("catalogs"), list) else []
    _require(len(evidence_rows) == int(summary.get("failedCatalogCount") or 0), "probe failed-catalog count mismatch")

    for raw in evidence_rows:
        _require(isinstance(raw, dict), "probe catalog row is not an object")
        language = _text(raw.get("language")).lower()
        country = _text(raw.get("country")).upper()
        key = (language, country)
        _require(key in rows, f"probe catalog {language}/{country} is absent from captured source metadata")
        row = rows[key]

        failed = int(raw.get("declaredFailedDetails") or 0)
        _require(raw.get("state") == "probed", f"probe catalog {language}/{country} was not fully probed")
        _require(raw.get("searchManifestCountStable") is True, f"probe catalog {language}/{country} manifest count drifted")
        _require(raw.get("candidateCountMatchesDeclaredFailures") is True, f"probe catalog {language}/{country} missing-ID count does not reconcile")
        _require(int(raw.get("unattributedDeclaredFailureCount") or 0) == 0, f"probe catalog {language}/{country} has unattributed failures")
        _require(int(raw.get("currentSearchCount") or 0) == int(raw.get("declaredUniqueVariants") or 0), f"probe catalog {language}/{country} current manifest differs from capture")
        _require(int(raw.get("currentCandidateCount") or 0) == failed, f"probe catalog {language}/{country} candidate count mismatch")
        _require(int(raw.get("probedCount") or 0) == failed, f"probe catalog {language}/{country} did not probe every missing ID")
        _require(raw.get("outcomes") == {"http-404": failed}, f"probe catalog {language}/{country} contains non-404 outcomes")

        _require(int(row.get("uniqueVariants") or 0) == int(raw.get("declaredUniqueVariants") or 0), f"captured {language}/{country} unique count changed")
        _require(int(row.get("hydratedVariants") or 0) == int(raw.get("declaredHydratedVariants") or 0), f"captured {language}/{country} hydrated count changed")
        _require(int(row.get("failedDetails") or 0) == failed, f"captured {language}/{country} failed count changed")

        rows_evidence = raw.get("evidence") if isinstance(raw.get("evidence"), list) else []
        ids: list[str] = []
        for item in rows_evidence:
            _require(isinstance(item, dict), "probe detail evidence is not an object")
            ident = _text(item.get("variantId"))
            _require(bool(ident), "probe detail evidence has empty provider variant ID")
            _require(item.get("outcome") == "http-404", f"provider variant {ident} did not reproduce as HTTP 404")
            _require(item.get("httpStatuses") == [404], f"provider variant {ident} has a non-pure-404 status set")
            _require(ident not in captured_ids, f"provider variant {ident} is already hydrated in captured catalog")
            _require(ident not in repaired_ids, f"provider variant {ident} appears in more than one failed catalog")
            repaired_ids.add(ident)
            ids.append(ident)

        _require(len(ids) == failed and len(set(ids)) == failed, f"probe catalog {language}/{country} evidence count mismatch")
        ids.sort()
        row["failedDetails"] = 0
        row["detailNotFoundCount"] = len(ids)
        row["detailNotFoundVariantIds"] = ids
        repaired_count += len(ids)
        repaired_catalogs += 1

    _require(repaired_count == declared, "repaired provider-ID total does not match probe summary")

    for row in catalogs:
        if not isinstance(row, dict):
            continue
        row.setdefault("detailNotFoundCount", 0)
        row.setdefault("detailNotFoundVariantIds", [])

    source["failedDetailCount"] = sum(
        int(row.get("failedDetails") or 0)
        for row in catalogs
        if isinstance(row, dict)
    )
    _require(source["failedDetailCount"] == 0, "capture still contains unaccounted failed details")
    source["detailNotFoundCount"] = repaired_count
    source["detailNotFoundPolicy"] = getattr(
        detail_not_found,
        "_POLICY",
        "search-manifest-app-access-rcu-404-accounted-v1",
    )
    source["detailNotFoundVariantIdsStored"] = True
    source["postCaptureFailedDetailProbeApplied"] = True
    source["postCaptureFailedDetailProbeCount"] = repaired_count
    source["postCaptureFailedDetailProbeCatalogCount"] = repaired_catalogs

    accounting_errors = detail_not_found.validation_errors(result)
    _require(not accounting_errors, f"detail-not-found accounting remains invalid: {accounting_errors[:5]}")

    result["complete"] = bool(reviewed._capture_complete(result))
    _require(result["complete"] is True, "repaired catalog is still not capture-complete")

    report = {
        "catalogVersion": _text(result.get("catalogVersion")),
        "repairedCatalogCount": repaired_catalogs,
        "repairedDetailNotFoundCount": repaired_count,
        "capturedVariantCount": len(captured_ids),
        "recipeGroupCount": len(result.get("recipes") or []),
        "ingredientCount": len(result.get("ingredients") or []),
        "complete": True,
        "providerVariantIdentityInferred": False,
        "recipeContentInvented": False,
        "networkRequestsPerformed": False,
        "secretsPersisted": False,
    }
    return result, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    result, report = repair(
        _load(Path(args.catalog).expanduser()),
        _load(Path(args.evidence).expanduser()),
    )
    output = Path(args.output).expanduser()
    _save(output, result)
    report_path = Path(args.report).expanduser()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**report, "outputBytes": output.stat().st_size}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
