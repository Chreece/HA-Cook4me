#!/usr/bin/env python3
"""Patch compiler + nutrition loader for explicit conflict-free high-confidence aliases."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPILER = ROOT / "tools/compile_release_catalog_semantics_v60.py"
RESOLVER = ROOT / "tools/resolve_reviewed_release_catalog_nutrition_targets_v60.py"
COMPILER_TEST = ROOT / "tests/test_semantic_high_confidence_syntax_aliases_v60.py"
NUTRITION_TEST = ROOT / "tests/test_nutrition_semantic_syntax_aliases_v60.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_compiler() -> None:
    text = COMPILER.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''STANDALONE_EQUIVALENCE_FILE = (\n    TOOLS / "release_catalog_semantic_standalone_equivalences.v1.json"\n)\n''',
        '''STANDALONE_EQUIVALENCE_FILE = (\n    TOOLS / "release_catalog_semantic_standalone_equivalences.v1.json"\n)\nHIGH_CONFIDENCE_SYNTAX_ALIAS_FILE = (\n    TOOLS / "release_catalog_semantic_high_confidence_syntax_aliases.v1.json"\n)\n''',
        "alias file constant",
    )
    text = replace_once(
        text,
        '''_ALLOWED_CLASSIFICATIONS = {"food", "equipment", "other", "ambiguous"}\n''',
        '''_HIGH_CONFIDENCE_SYNTAX_ALIAS_KIND = (\n    "cook4me-semantic-high-confidence-syntax-aliases"\n)\n_HIGH_CONFIDENCE_SYNTAX_ALIAS_POLICY = {\n    "providerIdentityAssigned": False,\n    "sourceLocalIdentityPreserved": True,\n    "highConfidenceOnly": True,\n    "safeSyntacticNormalizerRequired": True,\n    "cleanCanonicalTargetRequired": True,\n    "nutritionConflictTargetsExcluded": True,\n    "historicalReviewFilesMutated": False,\n}\n\n_ALLOWED_CLASSIFICATIONS = {"food", "equipment", "other", "ambiguous"}\n''',
        "alias policy constants",
    )

    loader = '''\n\ndef _load_high_confidence_syntax_alias_payload(path: Path) -> dict[str, Any]:\n    value = json.loads(path.read_text(encoding="utf-8"))\n    if not isinstance(value, dict):\n        raise RuntimeError(f"{path}: expected JSON object")\n    if value.get("schemaVersion") != 1:\n        raise RuntimeError(f"{path}: unsupported high-confidence syntax alias schemaVersion")\n    if value.get("kind") != _HIGH_CONFIDENCE_SYNTAX_ALIAS_KIND:\n        raise RuntimeError(f"{path}: unexpected high-confidence syntax alias kind")\n    policy = value.get("policy")\n    if not isinstance(policy, dict) or any(\n        policy.get(key) is not expected\n        for key, expected in _HIGH_CONFIDENCE_SYNTAX_ALIAS_POLICY.items()\n    ):\n        raise RuntimeError(f"{path}: unsafe high-confidence syntax alias policy")\n    items = value.get("items")\n    if not isinstance(items, list):\n        raise RuntimeError(f"{path}: high-confidence syntax alias items must be a list")\n    summary = value.get("summary") or {}\n    if int(summary.get("aliasConceptCount") or -1) != len(items):\n        raise RuntimeError(f"{path}: stale high-confidence syntax alias count")\n    return value\n'''
    text = replace_once(
        text,
        "\n\ndef iter_review_rows(\n",
        loader + "\n\ndef iter_review_rows(\n",
        "alias loader insertion",
    )

    alias_map = '''\n\ndef _high_confidence_syntax_alias_map(\n    review_rows: list[dict[str, Any]],\n    alias_payload: dict[str, Any] | None,\n    *,\n    alias_file: str = "",\n) -> dict[str, dict[str, Any]]:\n    if alias_payload is None:\n        return {}\n    if alias_payload.get("schemaVersion") != 1:\n        raise RuntimeError("unsupported high-confidence syntax alias schemaVersion")\n    if alias_payload.get("kind") != _HIGH_CONFIDENCE_SYNTAX_ALIAS_KIND:\n        raise RuntimeError("unexpected high-confidence syntax alias kind")\n    policy = alias_payload.get("policy")\n    if not isinstance(policy, dict) or any(\n        policy.get(key) is not expected\n        for key, expected in _HIGH_CONFIDENCE_SYNTAX_ALIAS_POLICY.items()\n    ):\n        raise RuntimeError("unsafe high-confidence syntax alias policy")\n    items = alias_payload.get("items")\n    if not isinstance(items, list):\n        raise RuntimeError("high-confidence syntax alias items must be a list")\n    summary = alias_payload.get("summary") or {}\n    if int(summary.get("aliasConceptCount") or -1) != len(items):\n        raise RuntimeError("stale high-confidence syntax alias count")\n\n    high_concepts = _high_confidence_concepts(review_rows)\n    source_ids_by_concept: dict[str, set[str]] = defaultdict(set)\n    for row in review_rows:\n        if (\n            row["confidence"] == "high"\n            and row["classification"] in _MERGEABLE_CLASSIFICATIONS\n        ):\n            concept_id = _semantic_concept_id(row["classification"], row["english"])\n            source_ids_by_concept[concept_id].add(\n                source_local_ingredient_id(row["language"], row["source"])\n            )\n\n    excluded = {\n        _text(value) for value in alias_payload.get("excludedConflictTargetConceptIds") or []\n        if _text(value)\n    }\n    if int(summary.get("excludedConflictGroupCount") or -1) != len(excluded):\n        raise RuntimeError("stale high-confidence syntax conflict-exclusion count")\n\n    out: dict[str, dict[str, Any]] = {}\n    target_ids: set[str] = set()\n    source_count = 0\n    group_keys: set[tuple[str, str]] = set()\n    for index, raw in enumerate(items, 1):\n        if not isinstance(raw, dict):\n            raise RuntimeError(f"high-confidence syntax alias item {index}: expected object")\n        old_id = _text(raw.get("oldConceptId"))\n        target_id = _text(raw.get("canonicalConceptId"))\n        if (\n            not old_id.startswith("concept:")\n            or not target_id.startswith("concept:")\n            or old_id == target_id\n        ):\n            raise RuntimeError(f"high-confidence syntax alias item {index}: invalid identity")\n        if old_id in out:\n            raise RuntimeError(f"duplicate high-confidence syntax alias: {old_id}")\n        if target_id in excluded:\n            raise RuntimeError(\n                f"nutrition-conflict target cannot receive syntax alias: {target_id}"\n            )\n        old_row = high_concepts.get(old_id)\n        target_row = high_concepts.get(target_id)\n        if old_row is None or target_row is None:\n            raise RuntimeError(\n                f"high-confidence syntax alias lacks reviewed high evidence: {old_id} -> {target_id}"\n            )\n        classification = _text(raw.get("classification")).lower()\n        old_english = _text(raw.get("oldCanonicalEnglish"))\n        target_english = _text(raw.get("canonicalEnglish"))\n        if (\n            classification not in _MERGEABLE_CLASSIFICATIONS\n            or old_row["classification"] != classification\n            or target_row["classification"] != classification\n        ):\n            raise RuntimeError(f"high-confidence syntax alias classification drift: {old_id}")\n        if old_english != old_row["english"]:\n            raise RuntimeError(f"high-confidence syntax alias old English drift: {old_id}")\n        if target_english != target_row["english"]:\n            raise RuntimeError(f"high-confidence syntax alias target English drift: {target_id}")\n        old_safe = _safe_syntactic_english(old_english)\n        target_safe = _safe_syntactic_english(target_english)\n        if _norm(old_safe) == _norm(old_english):\n            raise RuntimeError(f"high-confidence syntax alias old meaning is not syntax-changed: {old_id}")\n        if _norm(target_safe) != _norm(target_english):\n            raise RuntimeError(f"high-confidence syntax alias target is not clean canonical: {target_id}")\n        if _norm(old_safe) != _norm(target_english):\n            raise RuntimeError(f"high-confidence syntax alias normalizer mismatch: {old_id}")\n        expected_sources = source_ids_by_concept.get(old_id, set())\n        source_ids = {\n            _text(value) for value in raw.get("sourceIngredientIds") or [] if _text(value)\n        }\n        if source_ids != expected_sources:\n            raise RuntimeError(f"high-confidence syntax alias source set drift: {old_id}")\n        if raw.get("method") != "existing-safe-syntactic-normalizer":\n            raise RuntimeError(f"high-confidence syntax alias method drift: {old_id}")\n        rationale = _text(raw.get("rationale"))\n        if len(rationale) < 40:\n            raise RuntimeError(f"high-confidence syntax alias rationale too short: {old_id}")\n        source_count += len(source_ids)\n        group_keys.add((target_id, classification))\n        target_ids.add(target_id)\n        out[old_id] = {\n            "oldConceptId": old_id,\n            "canonicalConceptId": target_id,\n            "oldCanonicalEnglish": old_english,\n            "canonicalEnglish": target_english,\n            "classification": classification,\n            "sourceIngredientIds": sorted(source_ids),\n            "aliasFile": alias_file or "<inline-high-confidence-syntax-alias>",\n            "method": "explicit-reviewed-high-confidence-safe-syntax",\n            "rationale": rationale,\n        }\n\n    if set(out) & target_ids:\n        raise RuntimeError("high-confidence syntax aliases cannot form chains")\n    if int(summary.get("sourceIdentityCount") or -1) != source_count:\n        raise RuntimeError("stale high-confidence syntax alias source-identity count")\n    if int(summary.get("groupCount") or -1) != len(group_keys):\n        raise RuntimeError("stale high-confidence syntax alias group count")\n    return out\n'''
    text = replace_once(
        text,
        "\n\ndef _exact_confirmation_map(\n",
        alias_map + "\n\ndef _exact_confirmation_map(\n",
        "alias map insertion",
    )

    text = replace_once(
        text,
        '''    standalone_equivalence_payload: dict[str, Any] | None = None,\n    standalone_equivalence_file: str = "",\n) -> dict[str, Any]:\n''',
        '''    standalone_equivalence_payload: dict[str, Any] | None = None,\n    standalone_equivalence_file: str = "",\n    high_confidence_syntax_alias_payload: dict[str, Any] | None = None,\n    high_confidence_syntax_alias_file: str = "",\n) -> dict[str, Any]:\n''',
        "compile signature",
    )
    text = replace_once(
        text,
        '''    high_concepts = _high_confidence_concepts(review_rows)\n    confirmations, exact_count, equivalence_count, syntactic_count = _confirmation_map(\n''',
        '''    high_concepts = _high_confidence_concepts(review_rows)\n    high_confidence_syntax_aliases = _high_confidence_syntax_alias_map(\n        review_rows,\n        high_confidence_syntax_alias_payload,\n        alias_file=high_confidence_syntax_alias_file,\n    )\n    confirmations, exact_count, equivalence_count, syntactic_count = _confirmation_map(\n''',
        "compile alias map",
    )
    text = replace_once(
        text,
        '''    standalone = _standalone_disposition_map(\n''',
        '''    for confirmation in confirmations.values():\n        original = confirmation["confirmedConceptId"]\n        alias = high_confidence_syntax_aliases.get(original)\n        if alias is not None:\n            confirmation["originalConfirmedConceptId"] = original\n            confirmation["confirmedConceptId"] = alias["canonicalConceptId"]\n            confirmation["highConfidenceSyntaxAliasFile"] = alias["aliasFile"]\n            confirmation["highConfidenceSyntaxAliasMethod"] = alias["method"]\n\n    standalone = _standalone_disposition_map(\n''',
        "normalize confirmation targets",
    )

    text = replace_once(
        text,
        '''        standalone_equivalence = standalone_equivalences.get(source_id)\n\n        mergeable = (\n''',
        '''        standalone_equivalence = standalone_equivalences.get(source_id)\n\n        mergeable = (\n''',
        "loop anchor preflight",
    )
    text = replace_once(
        text,
        '''        explicitly_confirmed = confirmation is not None\n        if explicitly_confirmed:\n            concept_id = confirmation["confirmedConceptId"]\n            canonical_english = high_concepts[concept_id]["english"]\n        elif standalone_equivalence is not None:\n''',
        '''        explicitly_confirmed = confirmation is not None\n        raw_high_concept_id = (\n            _semantic_concept_id(classification, english) if mergeable else ""\n        )\n        high_confidence_syntax_alias = high_confidence_syntax_aliases.get(\n            raw_high_concept_id\n        )\n        if explicitly_confirmed:\n            concept_id = confirmation["confirmedConceptId"]\n            canonical_english = high_concepts[concept_id]["english"]\n        elif standalone_equivalence is not None:\n''',
        "loop alias lookup",
    )
    text = replace_once(
        text,
        '''        elif mergeable:\n            concept_id = _semantic_concept_id(classification, english)\n            canonical_english = english\n''',
        '''        elif high_confidence_syntax_alias is not None:\n            concept_id = high_confidence_syntax_alias["canonicalConceptId"]\n            canonical_english = high_confidence_syntax_alias["canonicalEnglish"]\n        elif mergeable:\n            concept_id = raw_high_concept_id\n            canonical_english = english\n''',
        "high alias concept resolution",
    )
    text = replace_once(
        text,
        '''        elif standalone_equivalence is not None:\n            merge_policy = "reviewed-source-local-standalone"\n        elif concept_mergeable:\n''',
        '''        elif standalone_equivalence is not None:\n            merge_policy = "reviewed-source-local-standalone"\n        elif high_confidence_syntax_alias is not None:\n            merge_policy = "reviewed-high-syntactic-alias"\n        elif concept_mergeable:\n''',
        "high alias merge policy",
    )
    text = replace_once(
        text,
        '''            if rationale := confirmation.get("confirmationRationale"):\n                identity["semanticConfirmationRationale"] = rationale\n''',
        '''            if rationale := confirmation.get("confirmationRationale"):\n                identity["semanticConfirmationRationale"] = rationale\n            if original := confirmation.get("originalConfirmedConceptId"):\n                identity["semanticConfirmationOriginalConceptId"] = original\n                identity["semanticConfirmationCanonicalConceptId"] = confirmation[\n                    "confirmedConceptId"\n                ]\n                identity["semanticConfirmationHighConfidenceSyntaxAliasFile"] = (\n                    confirmation["highConfidenceSyntaxAliasFile"]\n                )\n''',
        "confirmation alias receipt",
    )
    text = replace_once(
        text,
        '''        if standalone_disposition is not None:\n''',
        '''        if high_confidence_syntax_alias is not None:\n            identity["semanticHighConfidenceSyntaxAliasFile"] = (\n                high_confidence_syntax_alias["aliasFile"]\n            )\n            identity["semanticHighConfidenceSyntaxAliasOriginalConceptId"] = (\n                high_confidence_syntax_alias["oldConceptId"]\n            )\n            identity["semanticHighConfidenceSyntaxAliasCanonicalConceptId"] = (\n                high_confidence_syntax_alias["canonicalConceptId"]\n            )\n            identity["semanticHighConfidenceSyntaxAliasMethod"] = (\n                high_confidence_syntax_alias["method"]\n            )\n        if standalone_disposition is not None:\n''',
        "identity high alias receipt",
    )
    text = replace_once(
        text,
        '''            "highConfidenceExactEnglishMerge": True,\n''',
        '''            "highConfidenceExactEnglishMerge": True,\n            "explicitHighConfidenceSyntacticAlias": True,\n            "highConfidenceSyntacticAliasRequiresCleanCanonicalTarget": True,\n            "highConfidenceSyntacticAliasPreservesSafetyEligibility": True,\n''',
        "identity alias policy",
    )
    text = replace_once(
        text,
        '''            "syntacticConfirmedSourceLabels": syntactic_count,\n''',
        '''            "syntacticConfirmedSourceLabels": syntactic_count,\n            "highConfidenceSyntaxAliasConcepts": len(high_confidence_syntax_aliases),\n            "highConfidenceSyntaxAliasSourceLabels": sum(\n                len(row["sourceIngredientIds"])\n                for row in high_confidence_syntax_aliases.values()\n            ),\n''',
        "alias summary",
    )

    text = replace_once(
        text,
        '''    standalone_equivalence_path: Path | None = None,\n) -> dict[str, Any]:\n''',
        '''    standalone_equivalence_path: Path | None = None,\n    high_confidence_syntax_alias_path: Path | None = None,\n) -> dict[str, Any]:\n''',
        "compile_from_paths signature",
    )
    text = replace_once(
        text,
        '''    if standalone_equivalence_path is None and review_dir is not None:\n        candidate = review_dir / STANDALONE_EQUIVALENCE_FILE.name\n        if candidate.exists():\n            standalone_equivalence_path = candidate\n\n    confirmation_payload = None\n''',
        '''    if standalone_equivalence_path is None and review_dir is not None:\n        candidate = review_dir / STANDALONE_EQUIVALENCE_FILE.name\n        if candidate.exists():\n            standalone_equivalence_path = candidate\n\n    if high_confidence_syntax_alias_path is None and review_dir is not None:\n        candidate = review_dir / HIGH_CONFIDENCE_SYNTAX_ALIAS_FILE.name\n        if candidate.exists():\n            high_confidence_syntax_alias_path = candidate\n\n    confirmation_payload = None\n''',
        "auto alias path",
    )
    text = replace_once(
        text,
        '''    return compile_semantic_concepts(\n''',
        '''    high_confidence_syntax_alias_payload = None\n    high_confidence_syntax_alias_file = ""\n    if high_confidence_syntax_alias_path is not None:\n        high_confidence_syntax_alias_payload = (\n            _load_high_confidence_syntax_alias_payload(\n                high_confidence_syntax_alias_path\n            )\n        )\n        high_confidence_syntax_alias_file = high_confidence_syntax_alias_path.name\n\n    return compile_semantic_concepts(\n''',
        "load alias payload",
    )
    text = replace_once(
        text,
        '''        standalone_equivalence_file=standalone_equivalence_file,\n    )\n''',
        '''        standalone_equivalence_file=standalone_equivalence_file,\n        high_confidence_syntax_alias_payload=high_confidence_syntax_alias_payload,\n        high_confidence_syntax_alias_file=high_confidence_syntax_alias_file,\n    )\n''',
        "pass alias payload",
    )
    text = replace_once(
        text,
        '''    parser.add_argument(\n        "--standalone-equivalences",\n''',
        '''    parser.add_argument(\n        "--high-confidence-syntax-aliases",\n        default="",\n        help=(\n            "Optional explicit high-confidence safe-syntax alias JSON. When omitted, "\n            "release_catalog_semantic_high_confidence_syntax_aliases.v1.json is loaded "\n            "from the reviews directory when present."\n        ),\n    )\n    parser.add_argument(\n        "--standalone-equivalences",\n''',
        "CLI alias argument",
    )
    text = replace_once(
        text,
        '''    payload = compile_from_paths(\n        paths,\n''',
        '''    high_confidence_syntax_alias_path = (\n        Path(args.high_confidence_syntax_aliases).expanduser()\n        if args.high_confidence_syntax_aliases\n        else None\n    )\n    payload = compile_from_paths(\n        paths,\n''',
        "CLI alias path",
    )
    text = replace_once(
        text,
        '''        standalone_equivalence_path=standalone_equivalence_path,\n    )\n''',
        '''        standalone_equivalence_path=standalone_equivalence_path,\n        high_confidence_syntax_alias_path=high_confidence_syntax_alias_path,\n    )\n''',
        "CLI pass alias path",
    )
    COMPILER.write_text(text, encoding="utf-8")


def patch_resolver() -> None:
    text = RESOLVER.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''import snapshot_nutrition_review_checkpoint_v60 as checkpoint  # noqa: E402\n''',
        '''import snapshot_nutrition_review_checkpoint_v60 as checkpoint  # noqa: E402\nimport compile_release_catalog_semantics_v60 as semantic_compiler  # noqa: E402\n''',
        "resolver semantic compiler import",
    )
    helper = '''\n\ndef _semantic_syntax_aliases(root: Path) -> tuple[dict[str, dict[str, Any]], str]:\n    alias_path = root / semantic_compiler.HIGH_CONFIDENCE_SYNTAX_ALIAS_FILE.name\n    if not alias_path.exists():\n        return {}, ""\n    review_paths = semantic_compiler._review_paths(root)\n    if not review_paths:\n        raise RuntimeError(\n            "high-confidence syntax alias overlay exists without semantic review corpus"\n        )\n    review_payloads = [\n        (path.name, semantic_compiler._load_payload(path)) for path in review_paths\n    ]\n    review_rows = list(semantic_compiler.iter_review_rows(review_payloads))\n    payload = semantic_compiler._load_high_confidence_syntax_alias_payload(alias_path)\n    aliases = semantic_compiler._high_confidence_syntax_alias_map(\n        review_rows, payload, alias_file=alias_path.name\n    )\n    return aliases, alias_path.name\n'''
    text = replace_once(
        text,
        "\n\ndef load_reviews(root: Path = TOOLS) -> dict[str, dict[str, Any]]:\n",
        helper + "\n\ndef load_reviews(root: Path = TOOLS) -> dict[str, dict[str, Any]]:\n",
        "resolver alias helper",
    )
    text = replace_once(
        text,
        '''def load_reviews(root: Path = TOOLS) -> dict[str, dict[str, Any]]:\n    out: dict[str, dict[str, Any]] = {}\n''',
        '''def load_reviews(root: Path = TOOLS) -> dict[str, dict[str, Any]]:\n    aliases, alias_file = _semantic_syntax_aliases(root)\n    out: dict[str, dict[str, Any]] = {}\n''',
        "resolver load aliases",
    )
    text = replace_once(
        text,
        '''            target_id = _text(raw.get("reviewTargetId"))\n            try:\n''',
        '''            original_target_id = _text(raw.get("reviewTargetId"))\n            alias = aliases.get(original_target_id)\n            target_id = (\n                alias["canonicalConceptId"] if alias is not None else original_target_id\n            )\n            try:\n''',
        "resolver canonical target",
    )
    text = replace_once(
        text,
        '''            normalized = dict(raw)\n            normalized["reviewTargetId"] = target_id\n            normalized["fdcId"] = fdc_id\n            normalized["reviewFile"] = path.name\n            normalized.update(checkpoint.retained_reference_receipt(value, raw, path.name))\n''',
        '''            normalized = dict(raw)\n            normalized["reviewTargetId"] = target_id\n            normalized["fdcId"] = fdc_id\n            normalized["reviewFile"] = path.name\n            normalized.update(checkpoint.retained_reference_receipt(value, raw, path.name))\n            if alias is not None:\n                normalized["semanticSyntaxAliasOriginalReviewTargetId"] = original_target_id\n                normalized["semanticSyntaxAliasOriginalCanonicalEnglishName"] = _text(\n                    raw.get("canonicalEnglishName")\n                )\n                normalized["canonicalEnglishName"] = alias["canonicalEnglish"]\n                normalized["semanticSyntaxAliasFile"] = alias_file\n                normalized["semanticSyntaxAliasMethod"] = alias["method"]\n''',
        "resolver alias provenance",
    )
    RESOLVER.write_text(text, encoding="utf-8")


def write_tests() -> None:
    COMPILER_TEST.write_text(r'''from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "tools/compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_high_syntax_alias_test", MODULE)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

POLICY = {
    "providerIdentityAssigned": False,
    "sourceLocalIdentityPreserved": True,
    "highConfidenceOnly": True,
    "safeSyntacticNormalizerRequired": True,
    "cleanCanonicalTargetRequired": True,
    "nutritionConflictTargetsExcluded": True,
    "historicalReviewFilesMutated": False,
}


class HighConfidenceSyntaxAliasTests(unittest.TestCase):
    def _reviews(self):
        return [(
            "review.json",
            {
                "schemaVersion": 1,
                "kind": "cook4me-reviewed-keyless-ingredient-semantics",
                "items": [
                    {"language":"en","source":"Soy sauce","english":"Soy sauce","classification":"food","confidence":"high"},
                    {"language":"ja","source":"A soy","english":"A- soy sauce","classification":"food","confidence":"high"},
                ],
            },
        )]

    def _alias(self):
        old = mod._semantic_concept_id("food", "A- soy sauce")
        target = mod._semantic_concept_id("food", "Soy sauce")
        source = mod.source_local_ingredient_id("ja", "A soy")
        return {
            "schemaVersion":1,
            "kind":"cook4me-semantic-high-confidence-syntax-aliases",
            "policy": POLICY,
            "summary":{"aliasConceptCount":1,"groupCount":1,"sourceIdentityCount":1,"excludedConflictGroupCount":1},
            "excludedConflictTargetConceptIds":["concept:food:conflict"],
            "items":[{
                "oldConceptId":old,"canonicalConceptId":target,
                "oldCanonicalEnglish":"A- soy sauce","canonicalEnglish":"Soy sauce",
                "classification":"food","sourceIngredientIds":[source],
                "method":"existing-safe-syntactic-normalizer",
                "rationale":"High-confidence reviewed meaning differs only by tested safe recipe syntax and maps to the clean canonical target.",
            }],
        }

    def test_high_confidence_syntax_alias_preserves_safety_eligibility(self):
        result = mod.compile_semantic_concepts(
            self._reviews(),
            high_confidence_syntax_alias_payload=self._alias(),
            high_confidence_syntax_alias_file="aliases.json",
        )
        self.assertEqual(result["summary"]["semanticConcepts"], 1)
        self.assertEqual(result["summary"]["highConfidenceSyntaxAliasConcepts"], 1)
        self.assertEqual(result["summary"]["highConfidenceSyntaxAliasSourceLabels"], 1)
        source = mod.source_local_ingredient_id("ja", "A soy")
        target = mod._semantic_concept_id("food", "Soy sauce")
        self.assertEqual(result["sourceIdentityToConcept"][source], target)
        concept = result["concepts"][0]
        self.assertTrue(concept["nutritionEligible"])
        self.assertTrue(concept["dietEligible"])
        self.assertTrue(concept["allergenEligible"])
        identity = next(row for row in concept["sourceIdentities"] if row["ingredientId"] == source)
        self.assertEqual(identity["semanticHighConfidenceSyntaxAliasOriginalConceptId"], mod._semantic_concept_id("food", "A- soy sauce"))
        self.assertEqual(identity["semanticHighConfidenceSyntaxAliasCanonicalConceptId"], target)

    def test_alias_rejects_non_clean_target(self):
        payload = self._alias()
        payload["items"][0]["canonicalConceptId"] = payload["items"][0]["oldConceptId"]
        with self.assertRaises(RuntimeError):
            mod.compile_semantic_concepts(self._reviews(), high_confidence_syntax_alias_payload=payload)

    def test_repository_alias_overlay_is_exact_and_conflict_free(self):
        tools = ROOT / "tools"
        alias_path = tools / "release_catalog_semantic_high_confidence_syntax_aliases.v1.json"
        payload = mod._load_high_confidence_syntax_alias_payload(alias_path)
        self.assertEqual(payload["summary"]["aliasConceptCount"], 128)
        self.assertEqual(payload["summary"]["groupCount"], 112)
        self.assertEqual(payload["summary"]["sourceIdentityCount"], 130)
        self.assertEqual(payload["summary"]["excludedConflictGroupCount"], 11)
        rows = list(mod.iter_review_rows([(p.name, mod._load_payload(p)) for p in mod._review_paths(tools)]))
        aliases = mod._high_confidence_syntax_alias_map(rows, payload, alias_file=alias_path.name)
        self.assertEqual(len(aliases), 128)
        excluded = set(payload["excludedConflictTargetConceptIds"])
        self.assertFalse({row["canonicalConceptId"] for row in aliases.values()} & excluded)
        compiled = mod.compile_from_paths(mod._review_paths(tools))
        self.assertEqual(compiled["summary"]["highConfidenceSyntaxAliasConcepts"], 128)
        self.assertEqual(compiled["summary"]["highConfidenceSyntaxAliasSourceLabels"], 130)
        self.assertEqual(compiled["summary"]["needsSemanticConfirmationSourceLabels"], 0)
        concept_ids = {row["conceptId"] for row in compiled["concepts"]}
        self.assertFalse(set(aliases) & concept_ids)
        self.assertTrue({row["canonicalConceptId"] for row in aliases.values()} <= concept_ids)


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")

    NUTRITION_TEST.write_text(r'''from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

spec = importlib.util.spec_from_file_location(
    "cook4me_nutrition_syntax_alias_test",
    TOOLS / "resolve_reviewed_release_catalog_nutrition_targets_v60.py",
)
resolver = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(resolver)

import compile_release_catalog_semantics_v60 as semantic  # noqa: E402


class NutritionSemanticSyntaxAliasTests(unittest.TestCase):
    def _semantic_review(self):
        return {
            "schemaVersion":1,
            "kind":"cook4me-reviewed-keyless-ingredient-semantics",
            "items":[
                {"language":"en","source":"Soy sauce","english":"Soy sauce","classification":"food","confidence":"high"},
                {"language":"ja","source":"A soy","english":"A- soy sauce","classification":"food","confidence":"high"},
            ],
        }

    def _alias(self):
        old = semantic._semantic_concept_id("food", "A- soy sauce")
        target = semantic._semantic_concept_id("food", "Soy sauce")
        source = semantic.source_local_ingredient_id("ja", "A soy")
        return {
            "schemaVersion":1,
            "kind":"cook4me-semantic-high-confidence-syntax-aliases",
            "policy": semantic._HIGH_CONFIDENCE_SYNTAX_ALIAS_POLICY,
            "summary":{"aliasConceptCount":1,"groupCount":1,"sourceIdentityCount":1,"excludedConflictGroupCount":0},
            "excludedConflictTargetConceptIds":[],
            "items":[{
                "oldConceptId":old,"canonicalConceptId":target,
                "oldCanonicalEnglish":"A- soy sauce","canonicalEnglish":"Soy sauce",
                "classification":"food","sourceIngredientIds":[source],
                "method":"existing-safe-syntactic-normalizer",
                "rationale":"High-confidence reviewed meaning differs only by tested safe recipe syntax and maps to the clean canonical target.",
            }],
        }

    def _nutrition_doc(self, target_id, name, fdc_id):
        return {
            "schemaVersion":1,
            "kind":"cook4me-reviewed-nutrition-target-source",
            "policy":{
                "searchResultAutoAccepted":False,
                "exactFdcBindingRequired":True,
                "semanticConceptGroupingReviewed":True,
                "providerIdentityInference":False,
            },
            "items":[{"reviewTargetId":target_id,"reviewTargetKind":"semantic-concept","canonicalEnglishName":name,"fdcId":fdc_id}],
        }

    def test_loader_canonicalizes_historical_alias_without_mutating_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "release_catalog_reviewed_keyless_ingredients.v1.json").write_text(json.dumps(self._semantic_review()), encoding="utf-8")
            (root / semantic.HIGH_CONFIDENCE_SYNTAX_ALIAS_FILE.name).write_text(json.dumps(self._alias()), encoding="utf-8")
            old = semantic._semantic_concept_id("food", "A- soy sauce")
            target = semantic._semantic_concept_id("food", "Soy sauce")
            (root / "release_catalog_reviewed_nutrition_targets_001.v1.json").write_text(json.dumps(self._nutrition_doc(old, "A- soy sauce", 123)), encoding="utf-8")
            (root / "release_catalog_reviewed_nutrition_targets_002.v1.json").write_text(json.dumps(self._nutrition_doc(target, "Soy sauce", 123)), encoding="utf-8")
            reviews = resolver.load_reviews(root)
            self.assertEqual(set(reviews), {target})
            self.assertEqual(reviews[target]["fdcId"], 123)
            self.assertEqual(reviews[target]["canonicalEnglishName"], "Soy sauce")
            self.assertEqual(reviews[target]["semanticSyntaxAliasOriginalReviewTargetId"], old)
            self.assertEqual(reviews[target]["semanticSyntaxAliasOriginalCanonicalEnglishName"], "A- soy sauce")

    def test_loader_still_fails_closed_when_aliased_fdc_ids_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "release_catalog_reviewed_keyless_ingredients.v1.json").write_text(json.dumps(self._semantic_review()), encoding="utf-8")
            (root / semantic.HIGH_CONFIDENCE_SYNTAX_ALIAS_FILE.name).write_text(json.dumps(self._alias()), encoding="utf-8")
            old = semantic._semantic_concept_id("food", "A- soy sauce")
            target = semantic._semantic_concept_id("food", "Soy sauce")
            (root / "release_catalog_reviewed_nutrition_targets_001.v1.json").write_text(json.dumps(self._nutrition_doc(old, "A- soy sauce", 123)), encoding="utf-8")
            (root / "release_catalog_reviewed_nutrition_targets_002.v1.json").write_text(json.dumps(self._nutrition_doc(target, "Soy sauce", 456)), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "conflicting nutrition-target review"):
                resolver.load_reviews(root)


if __name__ == "__main__":
    unittest.main()
''', encoding="utf-8")


def main() -> int:
    patch_compiler()
    patch_resolver()
    write_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
