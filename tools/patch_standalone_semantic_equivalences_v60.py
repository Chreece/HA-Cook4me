#!/usr/bin/env python3
"""Patch v60 compiler for exact reviewed standalone-to-standalone equivalences."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / "tools/compile_release_catalog_semantics_v60.py"
COMPILER_TEST = ROOT / "tests/test_compile_release_catalog_semantics_v60.py"
STANDALONE = ROOT / "tools/release_catalog_semantic_standalone_dispositions.v1.json"
EQUIVALENCE = ROOT / "tools/release_catalog_semantic_standalone_equivalences.v1.json"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_compiler() -> None:
    text = COMPILER.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''STANDALONE_DISPOSITION_FILE = (\n    TOOLS / "release_catalog_semantic_standalone_dispositions.v1.json"\n)\n''',
        '''STANDALONE_DISPOSITION_FILE = (\n    TOOLS / "release_catalog_semantic_standalone_dispositions.v1.json"\n)\nSTANDALONE_EQUIVALENCE_FILE = (\n    TOOLS / "release_catalog_semantic_standalone_equivalences.v1.json"\n)\n''',
        "equivalence file constant",
    )

    text = replace_once(
        text,
        '''_ALLOWED_CLASSIFICATIONS = {"food", "equipment", "other", "ambiguous"}\n''',
        '''_STANDALONE_EQUIVALENCE_KIND = (\n    "cook4me-semantic-ingredient-standalone-equivalences"\n)\n_STANDALONE_EQUIVALENCE_POLICY = {\n    "providerIdentityAssigned": False,\n    "sourceLocalIdentityPreserved": True,\n    "targetRemainsStandalone": True,\n    "exactReviewedEnglishAndClassificationRequired": True,\n    "manualReviewRequired": True,\n    "safetyEligibilityGranted": False,\n}\n\n_ALLOWED_CLASSIFICATIONS = {"food", "equipment", "other", "ambiguous"}\n''',
        "equivalence policy constants",
    )

    loader = '''\n\ndef _load_standalone_equivalence_payload(path: Path) -> dict[str, Any]:\n    value = json.loads(path.read_text(encoding="utf-8"))\n    if not isinstance(value, dict):\n        raise RuntimeError(f"{path}: expected JSON object")\n    if value.get("schemaVersion") != 1:\n        raise RuntimeError(f"{path}: unsupported standalone equivalence schemaVersion")\n    if value.get("kind") != _STANDALONE_EQUIVALENCE_KIND:\n        raise RuntimeError(f"{path}: unexpected standalone equivalence kind")\n    policy = value.get("policy")\n    if not isinstance(policy, dict) or any(\n        policy.get(key) is not expected\n        for key, expected in _STANDALONE_EQUIVALENCE_POLICY.items()\n    ):\n        raise RuntimeError(f"{path}: unsafe standalone equivalence policy")\n    items = value.get("items")\n    if not isinstance(items, list):\n        raise RuntimeError(f"{path}: standalone equivalence items must be a list")\n    summary = value.get("summary") or {}\n    if int(summary.get("equivalenceCount") or -1) != len(items):\n        raise RuntimeError(f"{path}: stale standalone equivalence summary count")\n    return value\n'''
    text = replace_once(
        text,
        "\n\ndef iter_review_rows(\n",
        loader + "\n\ndef iter_review_rows(\n",
        "equivalence loader insertion",
    )

    equivalence_map = '''\n\ndef _standalone_equivalence_map(\n    review_rows: list[dict[str, Any]],\n    equivalence_payload: dict[str, Any] | None,\n    standalone: dict[str, dict[str, str]],\n    *,\n    equivalence_file: str = "",\n) -> dict[str, dict[str, str]]:\n    if equivalence_payload is None:\n        return {}\n    if equivalence_payload.get("schemaVersion") != 1:\n        raise RuntimeError("unsupported standalone equivalence schemaVersion")\n    if equivalence_payload.get("kind") != _STANDALONE_EQUIVALENCE_KIND:\n        raise RuntimeError("unexpected standalone equivalence kind")\n    policy = equivalence_payload.get("policy")\n    if not isinstance(policy, dict) or any(\n        policy.get(key) is not expected\n        for key, expected in _STANDALONE_EQUIVALENCE_POLICY.items()\n    ):\n        raise RuntimeError("unsafe standalone equivalence policy")\n    items = equivalence_payload.get("items")\n    if not isinstance(items, list):\n        raise RuntimeError("standalone equivalence items must be a list")\n    summary = equivalence_payload.get("summary") or {}\n    if int(summary.get("equivalenceCount") or -1) != len(items):\n        raise RuntimeError("stale standalone equivalence summary count")\n\n    rows_by_source_id = _rows_by_source_id(review_rows)\n    out: dict[str, dict[str, str]] = {}\n    used_ids: set[str] = set()\n    for index, raw in enumerate(items, 1):\n        if not isinstance(raw, dict):\n            raise RuntimeError(f"standalone equivalence item {index}: expected object")\n        source_id = _text(raw.get("sourceIngredientId"))\n        target_id = _text(raw.get("targetSourceIngredientId"))\n        if (\n            not source_id.startswith("local:")\n            or not target_id.startswith("local:")\n            or source_id == target_id\n        ):\n            raise RuntimeError(f"standalone equivalence item {index}: invalid source/target identity")\n        if source_id in used_ids or target_id in used_ids:\n            raise RuntimeError(\n                "standalone equivalence identities must form disjoint reviewed pairs: "\n                f"{source_id} -> {target_id}"\n            )\n        used_ids.update((source_id, target_id))\n        if source_id in standalone:\n            raise RuntimeError(\n                f"standalone equivalence source must be removed from standalone ledger: {source_id}"\n            )\n        target_disposition = standalone.get(target_id)\n        if (\n            target_disposition is None\n            or target_disposition.get("disposition")\n            != "reviewed-source-local-standalone"\n        ):\n            raise RuntimeError(\n                f"standalone equivalence target must remain standalone: {target_id}"\n            )\n\n        source_row = rows_by_source_id.get(source_id)\n        target_row = rows_by_source_id.get(target_id)\n        if source_row is None or target_row is None:\n            raise RuntimeError(\n                f"standalone equivalence pair lacks reviewed source evidence: {source_id} -> {target_id}"\n            )\n        if source_row["confidence"] == "high" or target_row["confidence"] == "high":\n            raise RuntimeError(\n                f"standalone equivalence cannot replace high-confidence semantics: {source_id} -> {target_id}"\n            )\n        classification = _text(raw.get("classification")).lower()\n        if (\n            classification not in _MERGEABLE_CLASSIFICATIONS\n            or source_row["classification"] != classification\n            or target_row["classification"] != classification\n        ):\n            raise RuntimeError(\n                f"standalone equivalence classification differs: {source_id} -> {target_id}"\n            )\n        source_english = _text(raw.get("sourceReviewedEnglish"))\n        target_english = _text(raw.get("targetReviewedEnglish"))\n        if source_english != source_row["english"]:\n            raise RuntimeError(\n                f"standalone equivalence sourceReviewedEnglish differs for {source_id}"\n            )\n        if target_english != target_row["english"]:\n            raise RuntimeError(\n                f"standalone equivalence targetReviewedEnglish differs for {target_id}"\n            )\n        if _norm(source_english) != _norm(target_english):\n            raise RuntimeError(\n                f"standalone equivalence reviewed meanings differ: {source_id} -> {target_id}"\n            )\n        rationale = _text(raw.get("rationale"))\n        if len(rationale) < 20:\n            raise RuntimeError(\n                f"standalone equivalence rationale is too short for {source_id}"\n            )\n        out[source_id] = {\n            "targetSourceIngredientId": target_id,\n            "targetConceptId": _source_concept_id(\n                target_row["language"], target_row["source"]\n            ),\n            "targetCanonicalEnglish": target_row["english"],\n            "equivalenceFile": equivalence_file or "<inline-standalone-equivalence>",\n            "rationale": rationale,\n        }\n    return out\n'''
    text = replace_once(
        text,
        "\n\ndef _confirmation_map(\n",
        equivalence_map + "\n\ndef _confirmation_map(\n",
        "equivalence map insertion",
    )

    text = replace_once(
        text,
        '''    standalone_payload: dict[str, Any] | None = None,\n    standalone_file: str = "",\n) -> dict[str, Any]:\n''',
        '''    standalone_payload: dict[str, Any] | None = None,\n    standalone_file: str = "",\n    standalone_equivalence_payload: dict[str, Any] | None = None,\n    standalone_equivalence_file: str = "",\n) -> dict[str, Any]:\n''',
        "compile signature",
    )

    text = replace_once(
        text,
        '''    standalone = _standalone_disposition_map(\n        review_rows,\n        standalone_payload,\n        standalone_file=standalone_file,\n    )\n    overlap = set(confirmations) & set(standalone)\n''',
        '''    standalone = _standalone_disposition_map(\n        review_rows,\n        standalone_payload,\n        standalone_file=standalone_file,\n    )\n    standalone_equivalences = _standalone_equivalence_map(\n        review_rows,\n        standalone_equivalence_payload,\n        standalone,\n        equivalence_file=standalone_equivalence_file,\n    )\n    overlap = set(confirmations) & set(standalone)\n''',
        "compile equivalence map",
    )
    text = replace_once(
        text,
        '''    if overlap:\n        raise RuntimeError(\n            "same source identity appears in semantic confirmation and standalone disposition: "\n            + ", ".join(sorted(overlap))\n        )\n\n    for row in review_rows:\n''',
        '''    if overlap:\n        raise RuntimeError(\n            "same source identity appears in semantic confirmation and standalone disposition: "\n            + ", ".join(sorted(overlap))\n        )\n    overlap = set(confirmations) & set(standalone_equivalences)\n    if overlap:\n        raise RuntimeError(\n            "same source identity appears in semantic confirmation and standalone equivalence: "\n            + ", ".join(sorted(overlap))\n        )\n    overlap = set(standalone) & set(standalone_equivalences)\n    if overlap:\n        raise RuntimeError(\n            "same source identity appears in standalone disposition and standalone equivalence: "\n            + ", ".join(sorted(overlap))\n        )\n\n    for row in review_rows:\n''',
        "compile overlap guards",
    )

    text = replace_once(
        text,
        '''        confirmation = confirmations.get(source_id)\n        standalone_disposition = standalone.get(source_id)\n\n        mergeable = (\n''',
        '''        confirmation = confirmations.get(source_id)\n        standalone_disposition = standalone.get(source_id)\n        standalone_equivalence = standalone_equivalences.get(source_id)\n\n        mergeable = (\n''',
        "loop equivalence lookup",
    )

    text = replace_once(
        text,
        '''        if explicitly_confirmed:\n            concept_id = confirmation["confirmedConceptId"]\n            canonical_english = high_concepts[concept_id]["english"]\n        elif mergeable:\n            concept_id = _semantic_concept_id(classification, english)\n            canonical_english = english\n        else:\n            concept_id = _source_concept_id(language, source)\n            canonical_english = english\n\n        concept_mergeable = mergeable or explicitly_confirmed\n        review_closed = concept_mergeable or standalone_disposition is not None\n        if standalone_disposition is not None:\n            merge_policy = standalone_disposition["disposition"]\n        elif concept_mergeable:\n            merge_policy = "reviewed-high-exact-english"\n        else:\n            merge_policy = "source-local-conservative"\n        safety_eligible = (\n            classification == "food" and standalone_disposition is None\n        )\n''',
        '''        if explicitly_confirmed:\n            concept_id = confirmation["confirmedConceptId"]\n            canonical_english = high_concepts[concept_id]["english"]\n        elif standalone_equivalence is not None:\n            concept_id = standalone_equivalence["targetConceptId"]\n            canonical_english = standalone_equivalence["targetCanonicalEnglish"]\n        elif mergeable:\n            concept_id = _semantic_concept_id(classification, english)\n            canonical_english = english\n        else:\n            concept_id = _source_concept_id(language, source)\n            canonical_english = english\n\n        concept_mergeable = mergeable or explicitly_confirmed\n        review_closed = bool(\n            concept_mergeable\n            or standalone_disposition is not None\n            or standalone_equivalence is not None\n        )\n        if standalone_disposition is not None:\n            merge_policy = standalone_disposition["disposition"]\n        elif standalone_equivalence is not None:\n            merge_policy = "reviewed-source-local-standalone"\n        elif concept_mergeable:\n            merge_policy = "reviewed-high-exact-english"\n        else:\n            merge_policy = "source-local-conservative"\n        safety_eligible = bool(\n            classification == "food"\n            and standalone_disposition is None\n            and standalone_equivalence is None\n        )\n''',
        "concept resolution logic",
    )

    text = replace_once(
        text,
        '''        if standalone_disposition is not None:\n            identity["semanticReviewDispositionFile"] = standalone_disposition[\n                "dispositionFile"\n            ]\n            identity["semanticReviewDisposition"] = standalone_disposition[\n                "disposition"\n            ]\n            identity["semanticReviewDispositionRationale"] = standalone_disposition[\n                "rationale"\n            ]\n        concept["sourceIdentities"].append(identity)\n''',
        '''        if standalone_disposition is not None:\n            identity["semanticReviewDispositionFile"] = standalone_disposition[\n                "dispositionFile"\n            ]\n            identity["semanticReviewDisposition"] = standalone_disposition[\n                "disposition"\n            ]\n            identity["semanticReviewDispositionRationale"] = standalone_disposition[\n                "rationale"\n            ]\n        if standalone_equivalence is not None:\n            identity["semanticStandaloneEquivalenceFile"] = standalone_equivalence[\n                "equivalenceFile"\n            ]\n            identity["semanticStandaloneEquivalenceTargetSourceIngredientId"] = (\n                standalone_equivalence["targetSourceIngredientId"]\n            )\n            identity["semanticStandaloneEquivalenceRationale"] = standalone_equivalence[\n                "rationale"\n            ]\n        concept["sourceIdentities"].append(identity)\n''',
        "identity equivalence receipt",
    )

    text = replace_once(
        text,
        '''    standalone_count = len(standalone)\n    reviewed_ambiguous_count = sum(\n''',
        '''    standalone_count = len(standalone)\n    standalone_equivalence_count = len(standalone_equivalences)\n    reviewed_ambiguous_count = sum(\n''',
        "equivalence summary count",
    )
    text = replace_once(
        text,
        '''            "explicitStandaloneReviewClosure": True,\n            "standaloneReviewClosureGrantsSafetyEligibility": False,\n''',
        '''            "explicitStandaloneReviewClosure": True,\n            "explicitStandaloneSemanticEquivalence": True,\n            "standaloneReviewClosureGrantsSafetyEligibility": False,\n            "standaloneSemanticEquivalenceGrantsSafetyEligibility": False,\n''',
        "identity policy equivalence",
    )
    text = replace_once(
        text,
        '''            "standaloneConfirmedSourceLabels": standalone_count,\n            "reviewedAmbiguousSourceLabels": reviewed_ambiguous_count,\n''',
        '''            "standaloneConfirmedSourceLabels": standalone_count,\n            "standaloneEquivalentSourceLabels": standalone_equivalence_count,\n            "reviewedAmbiguousSourceLabels": reviewed_ambiguous_count,\n''',
        "summary equivalence field",
    )

    text = replace_once(
        text,
        '''    standalone_path: Path | None = None,\n) -> dict[str, Any]:\n''',
        '''    standalone_path: Path | None = None,\n    standalone_equivalence_path: Path | None = None,\n) -> dict[str, Any]:\n''',
        "compile_from_paths signature",
    )
    text = replace_once(
        text,
        '''    if standalone_path is None and review_dir is not None:\n        candidate = review_dir / STANDALONE_DISPOSITION_FILE.name\n        if candidate.exists():\n            standalone_path = candidate\n\n    confirmation_payload = None\n''',
        '''    if standalone_path is None and review_dir is not None:\n        candidate = review_dir / STANDALONE_DISPOSITION_FILE.name\n        if candidate.exists():\n            standalone_path = candidate\n\n    if standalone_equivalence_path is None and review_dir is not None:\n        candidate = review_dir / STANDALONE_EQUIVALENCE_FILE.name\n        if candidate.exists():\n            standalone_equivalence_path = candidate\n\n    confirmation_payload = None\n''',
        "autodetect equivalence ledger",
    )
    text = replace_once(
        text,
        '''    standalone_payload = None\n    standalone_file = ""\n    if standalone_path is not None:\n        standalone_payload = _load_standalone_payload(standalone_path)\n        standalone_file = standalone_path.name\n\n    return compile_semantic_concepts(\n''',
        '''    standalone_payload = None\n    standalone_file = ""\n    if standalone_path is not None:\n        standalone_payload = _load_standalone_payload(standalone_path)\n        standalone_file = standalone_path.name\n\n    standalone_equivalence_payload = None\n    standalone_equivalence_file = ""\n    if standalone_equivalence_path is not None:\n        standalone_equivalence_payload = _load_standalone_equivalence_payload(\n            standalone_equivalence_path\n        )\n        standalone_equivalence_file = standalone_equivalence_path.name\n\n    return compile_semantic_concepts(\n''',
        "load equivalence ledger",
    )
    text = replace_once(
        text,
        '''        standalone_payload=standalone_payload,\n        standalone_file=standalone_file,\n    )\n''',
        '''        standalone_payload=standalone_payload,\n        standalone_file=standalone_file,\n        standalone_equivalence_payload=standalone_equivalence_payload,\n        standalone_equivalence_file=standalone_equivalence_file,\n    )\n''',
        "pass equivalence payload",
    )

    text = replace_once(
        text,
        '''    parser.add_argument(\n        "--standalone-dispositions",\n        default="",\n        help=(\n            "Optional conservative source-local review-disposition JSON. When omitted, "\n            "release_catalog_semantic_standalone_dispositions.v1.json is loaded "\n            "from the reviews directory when present."\n        ),\n    )\n    args = parser.parse_args()\n''',
        '''    parser.add_argument(\n        "--standalone-dispositions",\n        default="",\n        help=(\n            "Optional conservative source-local review-disposition JSON. When omitted, "\n            "release_catalog_semantic_standalone_dispositions.v1.json is loaded "\n            "from the reviews directory when present."\n        ),\n    )\n    parser.add_argument(\n        "--standalone-equivalences",\n        default="",\n        help=(\n            "Optional exact reviewed source-local equivalence JSON. When omitted, "\n            "release_catalog_semantic_standalone_equivalences.v1.json is loaded "\n            "from the reviews directory when present."\n        ),\n    )\n    args = parser.parse_args()\n''',
        "CLI equivalence option",
    )
    text = replace_once(
        text,
        '''    standalone_path = (\n        Path(args.standalone_dispositions).expanduser()\n        if args.standalone_dispositions\n        else None\n    )\n    payload = compile_from_paths(\n''',
        '''    standalone_path = (\n        Path(args.standalone_dispositions).expanduser()\n        if args.standalone_dispositions\n        else None\n    )\n    standalone_equivalence_path = (\n        Path(args.standalone_equivalences).expanduser()\n        if args.standalone_equivalences\n        else None\n    )\n    payload = compile_from_paths(\n''',
        "CLI equivalence path",
    )
    text = replace_once(
        text,
        '''        syntax_confirmation_path=syntax_confirmation_path,\n        standalone_path=standalone_path,\n    )\n''',
        '''        syntax_confirmation_path=syntax_confirmation_path,\n        standalone_path=standalone_path,\n        standalone_equivalence_path=standalone_equivalence_path,\n    )\n''',
        "CLI pass equivalence path",
    )

    COMPILER.write_text(text, encoding="utf-8")


def patch_ledgers() -> None:
    equivalence = json.loads(EQUIVALENCE.read_text(encoding="utf-8"))
    items = [row for row in equivalence.get("items") or [] if isinstance(row, dict)]
    if len(items) != 7 or int((equivalence.get("summary") or {}).get("equivalenceCount") or 0) != 7:
        raise RuntimeError("expected seven exact standalone equivalence pairs")
    source_ids = {row["sourceIngredientId"] for row in items}
    target_ids = {row["targetSourceIngredientId"] for row in items}
    if len(source_ids) != 7 or len(target_ids) != 7 or source_ids & target_ids:
        raise RuntimeError("equivalence pairs must contain fourteen distinct identities")

    standalone = json.loads(STANDALONE.read_text(encoding="utf-8"))
    standalone_items = [row for row in standalone.get("items") or [] if isinstance(row, dict)]
    by_id = {row.get("sourceIngredientId"): row for row in standalone_items}
    missing_sources = sorted(source_ids - set(by_id))
    missing_targets = sorted(target_ids - set(by_id))
    if missing_sources or missing_targets:
        raise RuntimeError(
            f"equivalence identities missing standalone evidence: sources={missing_sources} targets={missing_targets}"
        )
    for source_id in source_ids:
        if by_id[source_id].get("disposition") != "reviewed-source-local-standalone":
            raise RuntimeError(f"equivalence source is not mergeable standalone: {source_id}")
    for target_id in target_ids:
        if by_id[target_id].get("disposition") != "reviewed-source-local-standalone":
            raise RuntimeError(f"equivalence target is not retained standalone: {target_id}")

    remaining = [
        row for row in standalone_items
        if row.get("sourceIngredientId") not in source_ids
    ]
    ambiguous_count = sum(
        row.get("disposition") == "reviewed-ambiguous-source-fragment"
        for row in remaining
    )
    standalone["items"] = remaining
    standalone["summary"] = {
        "standaloneDispositionCount": len(remaining),
        "reviewedAmbiguousCount": ambiguous_count,
        "reviewedSourceLocalStandaloneCount": len(remaining) - ambiguous_count,
    }
    STANDALONE.write_text(
        json.dumps(standalone, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def patch_compiler_test() -> None:
    text = COMPILER_TEST.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''        standalone_count = len(standalone.get("items") or [])\n        review_total = total + standalone_count\n''',
        '''        standalone_count = len(standalone.get("items") or [])\n        standalone_equivalences = mod._load_standalone_equivalence_payload(\n            tools / "release_catalog_semantic_standalone_equivalences.v1.json"\n        )\n        standalone_equivalence_count = len(\n            standalone_equivalences.get("items") or []\n        )\n        review_total = total + standalone_count + standalone_equivalence_count\n''',
        "compiler test review total",
    )
    text = replace_once(
        text,
        '''        self.assertEqual(\n            confirmed["summary"]["standaloneConfirmedSourceLabels"],\n            standalone_count,\n        )\n        self.assertEqual(confirmed["summary"]["confirmedSourceLabels"], total)\n''',
        '''        self.assertEqual(\n            confirmed["summary"]["standaloneConfirmedSourceLabels"],\n            standalone_count,\n        )\n        self.assertEqual(\n            confirmed["summary"]["standaloneEquivalentSourceLabels"],\n            standalone_equivalence_count,\n        )\n        self.assertEqual(confirmed["summary"]["confirmedSourceLabels"], total)\n''',
        "compiler test equivalence summary",
    )
    text = replace_once(
        text,
        '''        self.assertEqual(\n            baseline["summary"]["semanticConcepts"]\n            - confirmed["summary"]["semanticConcepts"],\n            total,\n        )\n''',
        '''        self.assertEqual(\n            baseline["summary"]["semanticConcepts"]\n            - confirmed["summary"]["semanticConcepts"],\n            total + standalone_equivalence_count,\n        )\n''',
        "compiler test concept delta",
    )
    COMPILER_TEST.write_text(text, encoding="utf-8")


def main() -> int:
    patch_compiler()
    patch_ledgers()
    patch_compiler_test()
    print("patched standalone semantic equivalence support and removed 7 duplicate sources from standalone ledger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
