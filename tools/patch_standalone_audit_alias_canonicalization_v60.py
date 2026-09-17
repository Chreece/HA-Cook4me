#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "tools/audit_standalone_semantic_merge_candidates_v60.py"
TEST = ROOT / "tests/test_audit_standalone_semantic_merge_candidates_v60.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch_audit() -> None:
    text = AUDIT.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''    rows_by_source = semantics._rows_by_source_id(review_rows)\n    high_concepts = semantics._high_confidence_concepts(review_rows)\n    standalone = semantics._load_standalone_payload(\n''',
        '''    rows_by_source = semantics._rows_by_source_id(review_rows)\n\n    # Candidate target IDs must come from the fully compiled semantic graph, not\n    # from raw reviewed-English concepts. High-confidence syntax aliases can\n    # collapse a raw concept ID into a canonical concept; surfacing the old ID\n    # here would create stale review proposals.\n    compiled = semantics.compile_from_paths(review_paths)\n    compiled_concepts = {\n        str(row.get("conceptId") or ""): row\n        for row in compiled.get("concepts") or []\n        if isinstance(row, dict) and row.get("conceptId")\n    }\n    alias_old_ids: set[str] = set()\n    alias_path = review_root / semantics.HIGH_CONFIDENCE_SYNTAX_ALIAS_FILE.name\n    if alias_path.exists():\n        alias_payload = semantics._load_high_confidence_syntax_alias_payload(alias_path)\n        alias_old_ids = {\n            str(row.get("oldConceptId") or "")\n            for row in alias_payload.get("items") or []\n            if isinstance(row, dict) and row.get("oldConceptId")\n        }\n\n    canonical_high_concepts: dict[str, dict[str, Any]] = {}\n    for concept_id, concept in compiled_concepts.items():\n        classification = _text(concept.get("classification")).lower()\n        if classification not in semantics._MERGEABLE_CLASSIFICATIONS:\n            continue\n        if concept.get("needsSemanticConfirmation") is True:\n            continue\n        high_sources = [\n            row\n            for row in concept.get("sourceIdentities") or []\n            if isinstance(row, dict) and _text(row.get("confidence")).lower() == "high"\n        ]\n        if not high_sources:\n            continue\n        if concept_id in alias_old_ids:\n            raise RuntimeError(\n                f"compiled semantic graph still emits collapsed alias concept: {concept_id}"\n            )\n        canonical_high_concepts[concept_id] = {\n            "conceptId": concept_id,\n            "canonicalEnglish": _text(concept.get("canonicalEnglish")),\n            "classification": classification,\n            "reviewFiles": sorted(\n                {\n                    _text(row.get("reviewFile"))\n                    for row in high_sources\n                    if _text(row.get("reviewFile"))\n                }\n            ),\n        }\n\n    standalone = semantics._load_standalone_payload(\n''',
        "compiled canonical high-confidence targets",
    )

    text = replace_once(
        text,
        '''    high_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)\n    for concept_id, reviewed in high_concepts.items():\n        high_by_class[reviewed["classification"]].append(\n            {\n                "conceptId": concept_id,\n                "canonicalEnglish": reviewed["english"],\n                "classification": reviewed["classification"],\n                "reviewFile": reviewed["reviewFile"],\n            }\n        )\n''',
        '''    high_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)\n    for concept_id, reviewed in canonical_high_concepts.items():\n        high_by_class[reviewed["classification"]].append(reviewed)\n''',
        "canonical target index",
    )

    text = replace_once(
        text,
        '''                "targetCanonicalEnglish": target["canonicalEnglish"],\n                "targetReviewFile": target["reviewFile"],\n                "metrics": metrics,\n''',
        '''                "targetCanonicalEnglish": target["canonicalEnglish"],\n                "targetReviewFiles": target["reviewFiles"],\n                **(\n                    {"targetReviewFile": target["reviewFiles"][0]}\n                    if target["reviewFiles"]\n                    else {}\n                ),\n                "metrics": metrics,\n''',
        "candidate review provenance",
    )

    text = replace_once(
        text,
        '''            "standaloneLedgerMutated": False,\n            "ambiguousRowsExcludedFromMergeSuggestions": True,\n''',
        '''            "standaloneLedgerMutated": False,\n            "ambiguousRowsExcludedFromMergeSuggestions": True,\n            "highConfidenceTargetsCanonicalizedThroughCompiledSemanticGraph": True,\n            "collapsedHighConfidenceAliasTargetsExcluded": True,\n''',
        "audit policy proof",
    )

    text = replace_once(
        text,
        '''            "reviewedAmbiguousCount": len(ambiguous_rows),\n            "mergeableClassificationCounts": dict(sorted(class_counts.items())),\n''',
        '''            "reviewedAmbiguousCount": len(ambiguous_rows),\n            "canonicalHighConfidenceTargetConceptCount": len(canonical_high_concepts),\n            "collapsedHighConfidenceAliasConceptCount": len(alias_old_ids),\n            "mergeableClassificationCounts": dict(sorted(class_counts.items())),\n''',
        "audit summary canonical target counts",
    )

    AUDIT.write_text(text, encoding="utf-8")


def write_test() -> None:
    TEST.write_text(
        '''from __future__ import annotations\n\nimport importlib.util\nimport json\nfrom pathlib import Path\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\nTOOLS = ROOT / "tools"\nMODULE = TOOLS / "audit_standalone_semantic_merge_candidates_v60.py"\nspec = importlib.util.spec_from_file_location("cook4me_standalone_audit_test", MODULE)\naudit_mod = importlib.util.module_from_spec(spec)\nassert spec.loader is not None\nspec.loader.exec_module(audit_mod)\n\nSEMANTICS = TOOLS / "compile_release_catalog_semantics_v60.py"\nsem_spec = importlib.util.spec_from_file_location("cook4me_semantics_for_audit_test", SEMANTICS)\nsemantics = importlib.util.module_from_spec(sem_spec)\nassert sem_spec.loader is not None\nsem_spec.loader.exec_module(semantics)\n\n\nclass StandaloneSemanticAuditCanonicalizationTests(unittest.TestCase):\n    @classmethod\n    def setUpClass(cls):\n        cls.result = audit_mod.audit(TOOLS)\n        cls.compiled = semantics.compile_from_paths(semantics._review_paths(TOOLS))\n        alias_path = TOOLS / semantics.HIGH_CONFIDENCE_SYNTAX_ALIAS_FILE.name\n        cls.alias_payload = semantics._load_high_confidence_syntax_alias_payload(alias_path)\n\n    def test_high_confidence_candidate_targets_are_compiled_canonical_concepts(self):\n        compiled_ids = {row["conceptId"] for row in self.compiled.get("concepts") or []}\n        old_alias_ids = {\n            row["oldConceptId"] for row in self.alias_payload.get("items") or []\n        }\n        candidate_ids = {\n            candidate["targetConceptId"]\n            for row in self.result.get("items") or []\n            for candidate in row.get("candidateTargets") or []\n        }\n        self.assertTrue(candidate_ids <= compiled_ids)\n        self.assertFalse(candidate_ids & old_alias_ids)\n\n    def test_audit_reports_canonical_alias_exclusion_policy(self):\n        policy = self.result.get("policy") or {}\n        self.assertTrue(\n            policy.get("highConfidenceTargetsCanonicalizedThroughCompiledSemanticGraph")\n        )\n        self.assertTrue(policy.get("collapsedHighConfidenceAliasTargetsExcluded"))\n        self.assertEqual(\n            self.result["summary"]["collapsedHighConfidenceAliasConceptCount"],\n            self.alias_payload["summary"]["aliasConceptCount"],\n        )\n\n    def test_candidate_targets_have_high_confidence_reviewed_source(self):\n        concepts = {row["conceptId"]: row for row in self.compiled.get("concepts") or []}\n        candidate_ids = {\n            candidate["targetConceptId"]\n            for row in self.result.get("items") or []\n            for candidate in row.get("candidateTargets") or []\n        }\n        for concept_id in candidate_ids:\n            self.assertTrue(\n                any(\n                    source.get("confidence") == "high"\n                    for source in concepts[concept_id].get("sourceIdentities") or []\n                ),\n                concept_id,\n            )\n\n\nif __name__ == "__main__":\n    unittest.main()\n''',
        encoding="utf-8",
    )


def main() -> int:
    patch_audit()
    write_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
