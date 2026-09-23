#!/usr/bin/env python3
"""Activate newly reviewed nutrition onto the already compacted v60 catalog.

This is a post-activation delta overlay. It never recaptures Cook4Me/provider
content and never searches USDA. The current compact catalog is treated as the
immutable identity baseline; its unresolved nutrition targets are reconstructed,
only explicit reviewed target -> FDC bindings are resolved from pinned local USDA
bytes, and the resulting small reviewed cache is layered over the catalog.

Existing reviewed nutrition profiles are preserved by the v60 attach contract.
The final payload is compacted again and every count/provenance delta is checked
fail-closed before bytes are emitted.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
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

import build_release_catalog_v60_reviewed as builder  # type: ignore  # noqa: E402
import compact_release_catalog_runtime_v60 as compactor  # type: ignore  # noqa: E402
import fdc_reference_data_v60 as reference  # type: ignore  # noqa: E402
import prepare_post_activation_nutrition_review_targets_v60 as adapter  # type: ignore  # noqa: E402
import resolve_reviewed_release_catalog_nutrition_targets_offline_v60 as offline  # type: ignore  # noqa: E402
import resolve_reviewed_release_catalog_nutrition_targets_v60 as target_resolver  # type: ignore  # noqa: E402
import supplemental_nutrition_v60 as supplemental  # type: ignore  # noqa: E402


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _source(payload: dict[str, Any]) -> dict[str, Any]:
    value = payload.get("source")
    if not isinstance(value, dict):
        raise RuntimeError("catalog source metadata is missing")
    return value


def _counts(payload: dict[str, Any]) -> tuple[int, int, int]:
    recipes = [row for row in payload.get("recipes") or [] if isinstance(row, dict)]
    return (
        len(recipes),
        sum(len(row.get("variants") or []) for row in recipes),
        len(payload.get("ingredients") or []),
    )


def _manifest_receipts(source: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    value = _text(source.get("reviewedNutritionReferenceManifestSha256"))
    if value:
        out.add(value)
    for raw in source.get("reviewedNutritionReferenceManifestSha256s") or []:
        value = _text(raw)
        if value:
            out.add(value)
    return out


def _dataset_receipts(source: dict[str, Any]) -> set[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for raw in source.get("reviewedNutritionReferenceDatasets") or []:
        if not isinstance(raw, dict):
            continue
        item = (
            _text(raw.get("dataType")),
            _text(raw.get("releaseDate")),
            _text(raw.get("jsonSha256")),
        )
        if any(item):
            out.add(item)
    return out


def merge_reference_receipts(before: dict[str, Any], after: dict[str, Any]) -> None:
    """Preserve catalog-level USDA receipts across repeated runtime compaction.

    Compacted old profiles intentionally no longer contain per-profile maintenance
    hashes, so their catalog-level receipt is the only surviving proof. New
    profiles do carry the current pinned receipt until compaction. Never replace
    an older receipt with the new generation: retain the union.
    """
    manifests = _manifest_receipts(before) | _manifest_receipts(after)
    after.pop("reviewedNutritionReferenceManifestSha256", None)
    after.pop("reviewedNutritionReferenceManifestSha256s", None)
    if len(manifests) == 1:
        after["reviewedNutritionReferenceManifestSha256"] = next(iter(manifests))
    elif manifests:
        after["reviewedNutritionReferenceManifestSha256s"] = sorted(manifests)

    datasets = _dataset_receipts(before) | _dataset_receipts(after)
    if datasets:
        after["reviewedNutritionReferenceDatasets"] = [
            {"dataType": data_type, "releaseDate": release_date, "jsonSha256": sha}
            for data_type, release_date, sha in sorted(datasets)
        ]


def activate_catalog(
    catalog: dict[str, Any],
    *,
    review_root: Path,
    index: reference.ReferenceIndex,
    source_catalog_sha256: str = "",
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if int(catalog.get("schemaVersion") or 0) != 1:
        raise RuntimeError("expected release catalog schemaVersion=1")
    if catalog.get("complete") is not True:
        raise RuntimeError("post-activation nutrition overlay requires complete=true")

    before_source = deepcopy(_source(catalog))
    if before_source.get("runtimeCatalogCompacted") is not True:
        raise RuntimeError("post-activation nutrition overlay requires runtimeCatalogCompacted=true")
    if before_source.get("semanticCoverageComplete") is not True:
        raise RuntimeError("post-activation nutrition overlay requires semanticCoverageComplete=true")

    before_counts = _counts(catalog)
    before_required = int(before_source.get("reviewedNutritionRequiredCount") or 0)
    before_resolved = int(before_source.get("reviewedNutritionResolvedCount") or 0)
    if before_required <= 0 or not 0 <= before_resolved <= before_required:
        raise RuntimeError("invalid activated reviewed-nutrition accounting")
    before_pending = before_required - before_resolved

    # For activation we need the original unresolved target universe. Review-ID
    # subtraction is evidence-search optimization only, so explicitly disable it.
    _queue, queue_summary, targets, target_summary = adapter.prepare(
        catalog, reviewed_target_ids=()
    )
    activated_pending = int(queue_summary.get("activatedPendingNutritionCount") or 0)
    activated_targets = int(target_summary.get("activatedReviewTargetCount") or 0)
    if activated_pending != before_pending:
        raise RuntimeError(
            f"activated pending identity mismatch: catalog={before_pending} queue={activated_pending}"
        )
    if before_pending and activated_targets <= 0:
        raise RuntimeError("activated catalog has unresolved identities but no review targets")

    seeded_cache, supplemental_summary = supplemental.seed_cache(
        targets, {}, review_root=review_root
    )
    reviews = target_resolver.load_reviews(review_root)
    delta_cache, pending = offline.resolve_offline(targets, seeded_cache, reviews, index)
    resolution = pending.get("summary") if isinstance(pending.get("summary"), dict) else {}
    resolved_now_targets = int(resolution.get("resolvedNowReviewTargets") or 0)
    resolved_now_identities = int(resolution.get("resolvedNowIdentities") or 0)
    seeded_targets = int(
        supplemental_summary.get("supplementalResolvedNowReviewTargets") or 0
    )
    seeded_identities = int(
        supplemental_summary.get("supplementalResolvedNowIdentities") or 0
    )
    already_resolved_targets = int(
        resolution.get("alreadyResolvedReviewTargets") or 0
    )
    already_resolved_identities = int(
        resolution.get("alreadyResolvedIdentities") or 0
    )
    pending_targets = int(resolution.get("pendingReviewTargetCount") or 0)
    pending_identities = int(resolution.get("pendingIdentityCount") or 0)
    delta_targets = resolved_now_targets + seeded_targets
    delta_identities = resolved_now_identities + seeded_identities

    if already_resolved_targets != seeded_targets:
        raise RuntimeError(
            "supplemental review-target accounting disagrees with offline resolver"
        )
    if already_resolved_identities != seeded_identities:
        raise RuntimeError(
            "supplemental identity accounting disagrees with offline resolver"
        )
    if delta_targets <= 0 or delta_identities <= 0:
        raise RuntimeError("review corpus contains no new activatable nutrition bindings")
    if len(delta_cache) != delta_identities:
        raise RuntimeError(
            f"resolved cache/profile count mismatch: cache={len(delta_cache)} resolved={delta_identities}"
        )
    if pending_identities + delta_identities != before_pending:
        raise RuntimeError("nutrition activation lost unresolved ingredient identities")
    if pending_targets + delta_targets != activated_targets:
        raise RuntimeError("nutrition activation lost unresolved review targets")
    if supplemental_summary.get("networkRequestsPerformed") is not False:
        raise RuntimeError("supplemental nutrition resolution performed a network request")
    if resolution.get("networkRequestsPerformed") is not False:
        raise RuntimeError("post-activation nutrition resolution performed a network request")
    if _text(resolution.get("referenceManifestSha256")) != index.manifest_sha256:
        raise RuntimeError("offline nutrition resolver/reference manifest mismatch")

    hydrated = builder.apply_reviewed_nutrition(catalog, delta_cache)
    hydrated_source = _source(hydrated)
    expected_resolved = before_resolved + delta_identities
    if int(hydrated_source.get("reviewedNutritionRequiredCount") or 0) != before_required:
        raise RuntimeError("nutrition activation changed the required-identity denominator")
    if int(hydrated_source.get("reviewedNutritionResolvedCount") or 0) != expected_resolved:
        raise RuntimeError(
            "nutrition activation resolved-count delta differs from explicit reviewed identities"
        )
    if int(hydrated_source.get("reviewedNutritionRejectedEmbeddedCount") or 0) != 0:
        raise RuntimeError("nutrition activation rejected an existing embedded reviewed profile")
    if _counts(hydrated) != before_counts:
        raise RuntimeError("nutrition activation changed recipe/variant/ingredient counts")

    compacted, compact_summary = compactor.compact(hydrated)
    after_source = _source(compacted)
    if _counts(compacted) != before_counts:
        raise RuntimeError("post-activation compaction changed identity counts")
    if int(after_source.get("reviewedNutritionRequiredCount") or 0) != before_required:
        raise RuntimeError("post-activation compaction changed nutrition denominator")
    if int(after_source.get("reviewedNutritionResolvedCount") or 0) != expected_resolved:
        raise RuntimeError("post-activation compaction changed reviewed nutrition coverage")
    if int(after_source.get("failedDetailCount") or 0) != int(before_source.get("failedDetailCount") or 0):
        raise RuntimeError("nutrition activation changed failed-detail accounting")
    if int(after_source.get("detailNotFoundCount") or 0) != int(before_source.get("detailNotFoundCount") or 0):
        raise RuntimeError("nutrition activation changed detail-not-found accounting")

    merge_reference_receipts(before_source, after_source)
    after_source.update(
        {
            "postActivationNutritionOverlayApplied": True,
            "postActivationNutritionOverlayNetworkRequestsPerformed": False,
            "postActivationNutritionSourceCatalogSha256": source_catalog_sha256,
            "postActivationNutritionReferenceManifestSha256": index.manifest_sha256,
            "postActivationNutritionReviewCorpusTargetCount": len(reviews)
            + int(supplemental_summary.get("supplementalReviewCorpusTargetCount") or 0),
            "postActivationNutritionResolvedReviewTargetCount": delta_targets,
            "postActivationNutritionResolvedIdentityCount": delta_identities,
            "postActivationNutritionSupplementalReviewCorpusTargetCount": int(
                supplemental_summary.get("supplementalReviewCorpusTargetCount") or 0
            ),
            "postActivationNutritionSupplementalResolvedReviewTargetCount": seeded_targets,
            "postActivationNutritionSupplementalResolvedIdentityCount": seeded_identities,
            "postActivationNutritionPendingReviewTargetCount": pending_targets,
            "postActivationNutritionPendingIdentityCount": pending_identities,
        }
    )

    summary = {
        "catalogVersion": compacted.get("catalogVersion"),
        "sourceCatalogSha256": source_catalog_sha256,
        "referenceManifestSha256": index.manifest_sha256,
        "reviewCorpusTargetCount": len(reviews)
        + int(supplemental_summary.get("supplementalReviewCorpusTargetCount") or 0),
        "recipes": before_counts[0],
        "variants": before_counts[1],
        "ingredients": before_counts[2],
        "reviewedNutritionRequiredCountBefore": before_required,
        "reviewedNutritionResolvedCountBefore": before_resolved,
        "pendingIdentityCountBefore": before_pending,
        "activatedReviewTargetCountBefore": activated_targets,
        "newlyResolvedReviewTargetCount": delta_targets,
        "newlyResolvedIdentityCount": delta_identities,
        "newlyResolvedFdcReviewTargetCount": resolved_now_targets,
        "newlyResolvedFdcIdentityCount": resolved_now_identities,
        "newlyResolvedSupplementalReviewTargetCount": seeded_targets,
        "newlyResolvedSupplementalIdentityCount": seeded_identities,
        "supplementalReviewCorpusTargetCount": int(
            supplemental_summary.get("supplementalReviewCorpusTargetCount") or 0
        ),
        "reviewedNutritionResolvedCountAfter": expected_resolved,
        "reviewedNutritionRequiredCountAfter": before_required,
        "pendingReviewTargetCountAfter": pending_targets,
        "pendingIdentityCountAfter": pending_identities,
        "reviewedNutritionCoverageBefore": round(before_resolved / before_required, 8),
        "reviewedNutritionCoverageAfter": round(expected_resolved / before_required, 8),
        "networkRequestsPerformed": False,
        "runtimeCatalogCompacted": after_source.get("runtimeCatalogCompacted") is True,
        "runtimeRecipeNutritionOnDemand": after_source.get("runtimeRecipeNutritionOnDemand") is True,
        "referenceManifestReceipts": sorted(_manifest_receipts(after_source)),
        "referenceDatasetReceiptCount": len(_dataset_receipts(after_source)),
        "compactSummary": compact_summary,
    }
    return compacted, summary, delta_cache, pending


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, value: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--reference-manifest", required=True)
    parser.add_argument("--review-root", default=str(TOOLS))
    parser.add_argument("--output", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--delta-cache-output", required=True)
    parser.add_argument("--pending-output", required=True)
    args = parser.parse_args()

    catalog_path = Path(args.catalog).expanduser()
    raw = catalog_path.read_bytes()
    catalog = json.loads(raw.decode("utf-8"))
    if not isinstance(catalog, dict):
        raise SystemExit("catalog must be a JSON object")
    index = reference.ReferenceIndex(Path(args.reference_manifest).expanduser())
    result, summary, cache, pending = activate_catalog(
        catalog,
        review_root=Path(args.review_root).expanduser(),
        index=index,
        source_catalog_sha256=_sha256(raw),
    )
    output = Path(args.output).expanduser()
    summary_output = Path(args.summary_output).expanduser()
    cache_output = Path(args.delta_cache_output).expanduser()
    pending_output = Path(args.pending_output).expanduser()
    for path in (output, summary_output, cache_output, pending_output):
        if path.exists():
            raise SystemExit(f"output already exists: {path}")
    _write_json(output, result, compact=True)
    summary["outputBytes"] = output.stat().st_size
    summary["outputSha256"] = _sha256(output.read_bytes())
    _write_json(summary_output, summary)
    _write_json(cache_output, cache)
    _write_json(pending_output, pending)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
