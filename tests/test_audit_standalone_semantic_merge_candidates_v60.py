from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
MODULE = TOOLS / "audit_standalone_semantic_merge_candidates_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_standalone_audit_test", MODULE)
audit_mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(audit_mod)

SEMANTICS = TOOLS / "compile_release_catalog_semantics_v60.py"
sem_spec = importlib.util.spec_from_file_location("cook4me_semantics_for_audit_test", SEMANTICS)
semantics = importlib.util.module_from_spec(sem_spec)
assert sem_spec.loader is not None
sem_spec.loader.exec_module(semantics)


class StandaloneSemanticAuditCanonicalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = audit_mod.audit(TOOLS)
        cls.compiled = semantics.compile_from_paths(semantics._review_paths(TOOLS))
        alias_path = TOOLS / semantics.HIGH_CONFIDENCE_SYNTAX_ALIAS_FILE.name
        cls.alias_payload = semantics._load_high_confidence_syntax_alias_payload(alias_path)

    def test_high_confidence_candidate_targets_are_compiled_canonical_concepts(self):
        compiled_ids = {row["conceptId"] for row in self.compiled.get("concepts") or []}
        old_alias_ids = {
            row["oldConceptId"] for row in self.alias_payload.get("items") or []
        }
        candidate_ids = {
            candidate["targetConceptId"]
            for row in self.result.get("items") or []
            for candidate in row.get("candidateTargets") or []
        }
        self.assertTrue(candidate_ids <= compiled_ids)
        self.assertFalse(candidate_ids & old_alias_ids)

    def test_audit_reports_canonical_alias_exclusion_policy(self):
        policy = self.result.get("policy") or {}
        self.assertTrue(
            policy.get("highConfidenceTargetsCanonicalizedThroughCompiledSemanticGraph")
        )
        self.assertTrue(policy.get("collapsedHighConfidenceAliasTargetsExcluded"))
        self.assertEqual(
            self.result["summary"]["collapsedHighConfidenceAliasConceptCount"],
            self.alias_payload["summary"]["aliasConceptCount"],
        )

    def test_candidate_targets_have_high_confidence_reviewed_source(self):
        concepts = {row["conceptId"]: row for row in self.compiled.get("concepts") or []}
        candidate_ids = {
            candidate["targetConceptId"]
            for row in self.result.get("items") or []
            for candidate in row.get("candidateTargets") or []
        }
        for concept_id in candidate_ids:
            self.assertTrue(
                any(
                    source.get("confidence") == "high"
                    for source in concepts[concept_id].get("sourceIdentities") or []
                ),
                concept_id,
            )


if __name__ == "__main__":
    unittest.main()
