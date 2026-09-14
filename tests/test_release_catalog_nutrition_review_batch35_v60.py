"""Batch 35 documents unresolved evidence, never fabricates review progress."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import gzip
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
import snapshot_nutrition_review_checkpoint_v60 as cp  # noqa: E402
import nutrition_review_holds_v60 as holds  # noqa: E402
import prepare_nutrition_review_worklist_v60 as work  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/nutrition-batch35-evidence-requirements-v60.json.gz"
FIXTURE_SHA = "48730cc357f709ba881190fb36d95e0d061df0848bbac87713bef4d2a334520d"
LEDGER_SHA = "93bf4cdf796c5ecc688e8fe40a53f6cd5b844759f60d189b17f0841282186f59"
EVIDENCE_SHA = "e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac"


class Batch35EvidenceRequirementsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(gzip.decompress(FIXTURE.read_bytes()))
        cls.ledger = json.loads(work.LEDGER.read_text(encoding="utf-8"))
        # Deliberately a projection for pure-function unit tests, not a full audit input.
        cls.projection = {**cls.fixture["evidenceHeader"],
                          "items": cls.fixture["targets"] + cls.fixture["additionalSourceRows"]}
        cls.requirements = work.validate_ledger(cls.ledger, cls.projection, EVIDENCE_SHA)
        cls.checkpoint = cp.build_checkpoint(TOOLS)

    def test_28_exact_deferred_ids_and_byte_pinned_source(self):
        self.assertEqual(cp._digest(work.LEDGER.read_bytes()), LEDGER_SHA)
        self.assertEqual(cp._digest(FIXTURE.read_bytes()), FIXTURE_SHA)
        self.assertEqual(len(self.requirements), 28)
        self.assertEqual(len({r["reviewTargetId"] for r in self.fixture["targets"]}), 28)
        self.assertTrue(all(r["disposition"] == "deferred-no-binding" for r in self.requirements.values()))
        self.assertTrue(all("fdcId" not in r for r in self.requirements.values()))

    def test_235_earlier_review_files_and_4622_bindings_unchanged(self):
        prefix = "release_catalog_reviewed_nutrition_targets"
        files = [r for r in self.checkpoint["reviewFiles"]
                 if r["path"] == prefix + ".v1.json"
                 or r["path"].startswith(prefix + "_") and r["path"] < prefix + "_041"]
        self.assertEqual(len(files), 235)
        self.assertEqual(cp._digest(cp._encoded(files)), self.fixture["baseReviewFilesSha256"])
        names = {r["path"] for r in files}
        bindings = [r for r in self.checkpoint["recordedBindings"] if r["reviewFile"] in names]
        self.assertEqual(len(bindings), 4622)
        self.assertEqual(cp._digest(cp._encoded(bindings)), self.fixture["baseRecordedBindingsSha256"])
        self.assertFalse(set(self.requirements) & {r["reviewTargetId"] for r in bindings})

    def test_hold_registry_unchanged_and_deferrals_are_not_new_holds(self):
        held = holds.load_holds()
        self.assertEqual(len(held["targets"]), 12)
        self.assertEqual(held["registrySha256"], self.fixture["holdRegistrySha256"])
        self.assertFalse(set(self.requirements) & set(held["targets"]))

    def test_fixture_is_explicitly_a_projection_with_exact_original_target_hashes(self):
        self.assertFalse(self.fixture["fullSnapshotIncluded"])
        self.assertTrue(self.fixture["targetRowsAreExactOriginalRows"])
        self.assertEqual(self.fixture["sourceEvidenceSha256"], EVIDENCE_SHA)
        for row in self.fixture["targets"]:
            requirement = self.requirements[row["reviewTargetId"]]
            self.assertEqual(requirement["sourceTargetSha256"], cp._digest(cp._encoded(row)))
            self.assertEqual(requirement["usageCountAtReview"], row["usageCountSum"])

    def test_binding_approval_unsafe_policy_and_invalid_schema_are_rejected(self):
        for mutate in ("policy", "schema", "binding", "disposition", "reason"):
            ledger = deepcopy(self.ledger)
            if mutate == "policy": ledger["policy"]["bindingsApproved"] = 0
            elif mutate == "schema": ledger["schemaVersion"] = True
            elif mutate == "binding": ledger["items"][0]["fdcId"] = 123
            elif mutate == "disposition": ledger["items"][0]["disposition"] = "approved"
            else: ledger["items"][0]["reasonCode"] = "rank-one-accepted"
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                work.validate_ledger(ledger, self.projection, EVIDENCE_SHA)

    def test_full_file_manifest_and_catalog_drift_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "exact retained"):
            work.validate_ledger(self.ledger, self.projection, "b" * 64)
        for key in ("referenceManifestSha256", "catalogVersion"):
            evidence = deepcopy(self.projection)
            evidence[key] = "changed"
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "drift"):
                work.validate_ledger(self.ledger, evidence, EVIDENCE_SHA)

    def test_target_identity_usage_candidate_and_row_byte_drift_are_rejected(self):
        for field in ("canonicalEnglishName", "usageCountSum", "candidates", "queueIndex"):
            evidence = deepcopy(self.projection)
            row = evidence["items"][0]
            if field == "candidates": row[field][0]["description"] = "changed"
            elif field == "canonicalEnglishName": row[field] = "other ingredient"
            else: row[field] += 1
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "drift"):
                work.validate_ledger(self.ledger, evidence, EVIDENCE_SHA)
        ledger = deepcopy(self.ledger)
        ledger["items"][0]["usageCountAtReview"] = True
        with self.assertRaisesRegex(ValueError, "usage"):
            work.validate_ledger(ledger, self.projection, EVIDENCE_SHA)

    def test_duplicate_and_missing_full_target_ids_are_not_silently_skipped(self):
        ledger = deepcopy(self.ledger)
        ledger["items"].append(deepcopy(ledger["items"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate ledger"):
            work.validate_ledger(ledger, self.projection, EVIDENCE_SHA)
        evidence = deepcopy(self.projection)
        evidence["items"].append(deepcopy(evidence["items"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate evidence"):
            work.validate_ledger(self.ledger, evidence, EVIDENCE_SHA)
        evidence["items"] = evidence["items"][1:-1]
        with self.assertRaisesRegex(ValueError, "identity drift"):
            work.validate_ledger(self.ledger, evidence, EVIDENCE_SHA)

    def test_every_requirement_is_actionable_not_a_semantic_approval(self):
        for row in self.requirements.values():
            self.assertGreater(len(row["reason"]), 100)
            self.assertGreater(len(row["evidenceRequired"]), 80)
            self.assertTrue(row["referenceQuery"].strip())
        self.assertFalse(self.ledger["policy"]["deferredTargetsCountAsComplete"])
        self.assertFalse(self.ledger["policy"]["heldBindingsReleased"])

    def test_index_preserves_every_occurrence_and_original_candidate_hash(self):
        index = work.build_reference_index(self.projection, set())
        self.assertFalse(index["selectionPerformed"])
        self.assertFalse(index["semanticApprovalPerformed"])
        expected = {(r["reviewTargetId"], c["fdcId"], c["localEvidenceRank"]): c
                    for r in self.projection["items"] for c in r["candidates"]}
        self.assertEqual(index["candidateOccurrenceCount"], len(expected))
        self.assertEqual([r["fdcId"] for r in index["records"]],
                         sorted({key[1] for key in expected}))
        for row in index["records"]:
            for occurrence in row["occurrences"]:
                candidate = expected[(occurrence["sourceEvidenceTargetId"], row["fdcId"],
                                      occurrence["sourceEvidenceCandidateRank"])]
                self.assertEqual(occurrence["sourceCandidateSha256"], cp._digest(cp._encoded(candidate)))

    def test_lexical_potato_starch_hit_is_composite_food_not_an_approval(self):
        index = work.build_reference_index(self.projection, set())
        result = work.search_references(index, "POTATO starch")
        self.assertGreater(result["matchRecordCount"], 0)
        self.assertIn(171861, {r["fdcId"] for r in result["matches"]})
        self.assertTrue(any("Rolls, gluten-free" in o["description"]
                            for r in result["matches"] for o in r["occurrences"]))
        self.assertFalse(result["selectionPerformed"])
        self.assertFalse(result["lexicalSearchIsIdentityProof"])
        self.assertFalse(work.search_references(index, "not-present-unique-word")["zeroMatchesProveFoodAbsent"])

    def test_search_excludes_held_locator_not_every_occurrence_of_same_fdc_id(self):
        source = deepcopy(self.projection["items"][0])
        alternate = deepcopy(source)
        alternate["reviewTargetId"] = "concept:food:independent-unheld-location"
        evidence = {"items": [source, alternate]}
        index = work.build_reference_index(evidence, {source["reviewTargetId"]})
        query = source["candidates"][0]["description"]
        result = work.search_references(index, query)
        self.assertGreater(result["heldLocatorOccurrencesExcluded"], 0)
        self.assertTrue(result["matches"])
        self.assertTrue(all(o["sourceEvidenceTargetId"] == alternate["reviewTargetId"]
                            for r in result["matches"] for o in r["occurrences"]))

    def test_index_rejects_duplicate_rows_candidate_ids_and_invalid_ids(self):
        for mutate in ("row", "candidate", "bool", "float", "description", "rank"):
            evidence = deepcopy(self.projection)
            first = evidence["items"][0]
            if mutate == "row": evidence["items"].append(deepcopy(first))
            elif mutate == "candidate": first["candidates"].append(deepcopy(first["candidates"][0]))
            elif mutate == "bool": first["candidates"][0]["fdcId"] = True
            elif mutate == "float": first["candidates"][0]["fdcId"] = 12.5
            elif mutate == "description": first["candidates"][0]["description"] = ""
            else: first["candidates"][0]["localEvidenceRank"] = 0
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                work.build_reference_index(evidence, set())

    def test_queries_require_nonempty_and_terms_and_do_not_rank_by_search_score(self):
        index = work.build_reference_index(self.projection, set())
        for query in ("", "  "):
            with self.assertRaisesRegex(ValueError, "empty"):
                work.search_references(index, query)
        result = work.search_references(index, "potato starch")
        for row in result["matches"]:
            self.assertTrue(all("potato" in o["description"].lower() and "starch" in o["description"].lower()
                                for o in row["occurrences"]))
        self.assertEqual([r["fdcId"] for r in result["matches"]],
                         sorted(r["fdcId"] for r in result["matches"]))

    def test_partition_keeps_all_deferred_targets_unresolved_and_preserves_remaining(self):
        remaining = deepcopy(self.projection["items"])
        before = deepcopy(remaining)
        annotated, untriaged = work.partition_requirements(self.requirements, remaining, {}, set())
        self.assertEqual(remaining, before)
        self.assertEqual(len(annotated), 28)
        self.assertTrue(all(r["currentStatus"] == "unreviewed-needs-evidence" for r in annotated))
        self.assertEqual(untriaged, [r for r in before if r["reviewTargetId"] not in self.requirements])
        self.assertEqual(len(remaining), len(untriaged) + 28)

    def test_later_record_and_current_hold_have_explicit_noncertifying_status(self):
        target = next(iter(self.requirements))
        one = {target: self.requirements[target]}
        annotated, _ = work.partition_requirements(one, [], {target: {"fdcId": 123}}, set())
        self.assertEqual(annotated[0]["currentStatus"], "recorded-later-not-certified-by-this-ledger")
        annotated, _ = work.partition_requirements(one, [], {target: {"fdcId": 123}}, {target})
        self.assertEqual(annotated[0]["currentStatus"], "held-requires-separate-rereview")
        with self.assertRaisesRegex(ValueError, "absent"):
            work.partition_requirements(one, [], {}, set())

    def test_partition_rejects_duplicate_or_previously_recorded_remaining_ids(self):
        row = self.projection["items"][0]
        with self.assertRaisesRegex(ValueError, "duplicates"):
            work.partition_requirements({}, [row, row], {}, set())
        with self.assertRaisesRegex(ValueError, "overlaps"):
            work.partition_requirements({}, [row], {row["reviewTargetId"]: {}}, set())

    def test_pure_helpers_are_deterministic_and_do_not_mutate_inputs(self):
        evidence = deepcopy(self.projection)
        ledger = deepcopy(self.ledger)
        before = deepcopy((evidence, ledger))
        first = work.build_reference_index(evidence, set())
        result = work.search_references(first, "potato starch")
        work.validate_ledger(ledger, evidence, EVIDENCE_SHA)
        self.assertEqual((evidence, ledger), before)
        self.assertEqual(first, work.build_reference_index(evidence, set()))
        result["matches"][0]["occurrences"][0]["description"] = "changed return value"
        self.assertEqual(first, work.build_reference_index(evidence, set()))

    def test_real_audit_rejects_subset_instead_of_claiming_full_queue_readiness(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "subset.json"
            path.write_bytes(cp._encoded(self.projection))
            with self.assertRaisesRegex(ValueError, "exact retained candidate snapshot"):
                work.build_outputs(path)
            output = Path(temp) / "output"
            with redirect_stderr(io.StringIO()):
                self.assertEqual(work.main(["--evidence", str(path), "--output", str(output)]), 1)
            self.assertFalse(output.exists())

    def test_cli_nonzero_incomplete_status_compact_output_and_no_overwrite(self):
        summary = {"remainingEvidenceTargetCount": 1697, "heldReviewTargetCount": 12,
                   "unheldProvenanceMismatchCount": 0, "newBindingsApproved": 0}
        fake = {"summary.json": summary, "worklist.json": {"approved": False}}
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "original.json"
            source.write_text("unchanged")
            out = Path(temp) / "report"
            args = ["--evidence", str(source), "--output", str(out)]
            with patch.object(work, "build_outputs", return_value=fake) as build, redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(work.main(args), 2)
                self.assertEqual(json.loads(stdout.getvalue()), summary)
                build.assert_called_once()
            original_output = (out / "summary.json").read_bytes()
            with patch.object(work, "build_outputs") as build, redirect_stderr(io.StringIO()):
                self.assertEqual(work.main(args), 1)
                build.assert_not_called()
            self.assertEqual((out / "summary.json").read_bytes(), original_output)
            self.assertEqual(source.read_text(), "unchanged")

    def test_cli_zero_requires_no_remaining_holds_or_unexplained_mismatches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for i, counts in enumerate(((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1))):
                summary = dict(zip(("remainingEvidenceTargetCount", "heldReviewTargetCount",
                                    "unheldProvenanceMismatchCount"), counts))
                with patch.object(work, "build_outputs", return_value={"summary.json": summary}), redirect_stdout(io.StringIO()):
                    status = work.main(["--evidence", str(root / "not-used"), "--output", str(root / str(i))])
                self.assertEqual(status, 0 if counts == (0, 0, 0) else 2)

    def _audit_fixture(self):
        return {"evidenceSha256": EVIDENCE_SHA,
                "reviewFilesSha256": self.checkpoint["reviewFilesSha256"],
                "registrySha256": self.fixture["holdRegistrySha256"],
                "heldTargets": list(holds.load_holds()["targets"].values()),
                "remainingUnheldCandidates": deepcopy(self.fixture["targets"]),
                "readyForManualReview": False, "readyForUnheldManualReview": True,
                "summary": {"remainingEvidenceTargetCount": 28,
                            "heldReviewTargetCount": 12, "provenanceMismatchCount": 11,
                            "unheldProvenanceMismatchCount": 0}}

    def test_build_preserves_audit_gates_and_entire_completeness_queue(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "projection.json"
            source.write_bytes(cp._encoded(self.projection))
            digest = cp._digest(source.read_bytes())
            ledger = deepcopy(self.ledger)
            ledger["sourceEvidenceSha256"] = digest
            ledger_path = Path(temp) / "ledger.json"
            ledger_path.write_bytes(cp._encoded(ledger))
            audit = self._audit_fixture()
            audit["evidenceSha256"] = digest
            # Reproduce the exact Batch 35 review baseline. Later explicit review
            # batches may legitimately record IDs from this historical 28-row fixture.
            previous_files = [r for r in self.checkpoint["reviewFiles"]
                              if r["path"] < "release_catalog_reviewed_nutrition_targets_041.v1.json"]
            previous_names = {r["path"] for r in previous_files}
            previous_bindings = [r for r in self.checkpoint["recordedBindings"]
                                 if r["reviewFile"] in previous_names]
            historical = dict(self.checkpoint)
            historical["reviewFiles"] = previous_files
            historical["recordedBindings"] = previous_bindings
            historical["reviewFilesSha256"] = cp._digest(cp._encoded(previous_files))
            historical["recordedBindingsSha256"] = cp._digest(cp._encoded(previous_bindings))
            audit["reviewFilesSha256"] = historical["reviewFilesSha256"]
            before = deepcopy(audit)
            with patch.object(holds, "audit", return_value=audit) as audited, \
                 patch.object(work.checkpoint, "build_checkpoint", return_value=historical):
                outputs = work.build_outputs(source, ledger_path=ledger_path, queries=["potato starch"])
                audited.assert_called_once()
            self.assertEqual(audit, before)
            self.assertEqual(outputs["remaining.json"]["items"], self.fixture["targets"])
            self.assertEqual(outputs["untriaged.json"]["items"], [])
            self.assertFalse(outputs["worklist.json"]["readyForManualReview"])
            self.assertTrue(outputs["worklist.json"]["readyForUnheldManualReview"])
            self.assertFalse(outputs["worklist.json"]["catalogNutritionApprovalGranted"])
            self.assertEqual(outputs["summary.json"]["remainingEvidenceTargetCount"], 28)
            self.assertEqual(outputs["summary.json"]["newBindingsApproved"], 0)
            self.assertEqual(outputs["summary.json"]["heldReviewTargetCount"], 12)
            self.assertEqual(outputs["hold-audit.json"], before)

    def test_build_rejects_evidence_changed_since_initial_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "projection.json"
            source.write_bytes(cp._encoded(self.projection))
            audit = self._audit_fixture()
            audit["evidenceSha256"] = "0" * 64
            with patch.object(holds, "audit", return_value=audit):
                with self.assertRaisesRegex(ValueError, "evidence changed during audit"):
                    work.build_outputs(source)

    def test_build_rejects_review_files_changed_since_initial_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "projection.json"
            source.write_bytes(cp._encoded(self.projection))
            digest = cp._digest(source.read_bytes())
            ledger = deepcopy(self.ledger)
            ledger["sourceEvidenceSha256"] = digest
            ledger_path = Path(temp) / "ledger.json"
            ledger_path.write_bytes(cp._encoded(ledger))
            audit = self._audit_fixture()
            audit.update(evidenceSha256=digest, reviewFilesSha256="0" * 64)
            with patch.object(holds, "audit", return_value=audit):
                with self.assertRaisesRegex(ValueError, "review files changed during audit"):
                    work.build_outputs(source, ledger_path=ledger_path)


if __name__ == "__main__":
    unittest.main()
