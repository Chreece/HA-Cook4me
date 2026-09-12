from __future__ import annotations

from copy import deepcopy
import gzip
import json
import re
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "tools", ROOT / "tests", ROOT / "custom_components/cook4me"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import nutrition_review_holds_v60 as holds
import reviewed_nutrition_v60 as provenance
import resolve_reviewed_release_catalog_nutrition_targets_v60 as targets
import resolve_reviewed_release_catalog_nutrition_targets_offline_v60 as offline
import resolve_reviewed_release_catalog_nutrition_v60 as exact
import snapshot_release_catalog_nutrition_queue_v60 as queue_tool
import test_release_catalog_nutrition_review_targets_v60 as target_fixtures
import test_release_catalog_nutrition_review_reuse_proposal_v60 as reuse_fixtures
import test_release_catalog_v60_finalizer as finalizer_fixtures
import test_validate_release_catalog_v60 as validator_fixtures


def evidence_fixture() -> dict:
    path = ROOT / "tests/fixtures/nutrition-hold-evidence-subset-v60.json.gz"
    return json.loads(gzip.decompress(path.read_bytes()))


def old_profile(hold: dict, member: str, *, tagged: bool = True) -> dict:
    # Synthetic nutrient values test provenance, not nutritional correctness.
    value = finalizer_fixtures.reviewed_profile(
        member, hold["canonicalEnglishName"], 42.0, hold["fdcId"]
    )
    value["reviewFile"] = hold["reviewFile"]
    if tagged:
        value["nutritionReviewTargetId"] = hold["reviewTargetId"]
    return value


def held_queue(rows: list[dict]) -> dict:
    queue, _summary = target_fixtures.compactor.compact(target_fixtures.queue())
    queue["targets"] = [{
        "reviewTargetId": row["reviewTargetId"],
        "reviewTargetKind": row["reviewTargetKind"],
        "canonicalEnglishName": row["canonicalEnglishName"],
        "semanticConceptId": row["reviewTargetId"],
        "memberIngredientIds": list(row["memberIngredientIds"]),
    } for row in rows]
    return queue


class NutritionReviewHoldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = holds.load_holds()
        cls.rows = list(cls.index["targets"].values())
        cls.base_checkpoint = holds.checkpoint.build_checkpoint(holds.TOOLS)
        cls.base_semantics = holds.semantics.compile_from_paths(holds.semantics._review_paths())
        cls.powder = cls.index["targets"]["concept:food:4b699a7031f660ff4dc1"]
        cls.blend = cls.index["targets"]["concept:food:222a1991f9c8e3bef676"]

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "holds.json"
        self.registry = json.loads(holds.REGISTRY.read_text(encoding="utf-8"))

    def load(self):
        self.path.write_text(json.dumps(self.registry), encoding="utf-8")
        # Validation unit cases reuse immutable fixtures. The separate source-byte
        # drift and repository-contract tests exercise real source reads.
        with patch.object(holds.checkpoint, "build_checkpoint", return_value=self.base_checkpoint), patch.object(
            holds.semantics, "compile_from_paths", return_value=self.base_semantics
        ):
            return holds.load_holds(self.path)

    def test_twelve_holds_pin_original_bindings_and_twenty_two_member_ids(self):
        self.assertEqual(len(self.rows), 12)
        members = [m for r in self.rows for m in r["memberIngredientIds"]]
        self.assertEqual(len(members), 22)
        self.assertEqual(len(set(members)), 22)
        self.assertEqual(sum(m.startswith("local:") for m in members), 21)
        self.assertEqual(self.powder["reasonCode"], "food_form_mismatch")
        self.assertEqual(self.blend["reasonCode"], "composition_mismatch")
        for row in self.rows:
            self.assertEqual(holds.find_hold(row["reviewTargetId"])["fdcId"], row["fdcId"])
            for member in row["memberIngredientIds"]:
                self.assertEqual(holds.find_hold(member)["reviewTargetId"], row["reviewTargetId"])

    def test_historical_review_corpus_is_unchanged(self):
        cp = holds.checkpoint.build_checkpoint(holds.TOOLS)
        # Pin historical files only; future disjoint review batches may be added.
        prior = {r["path"] for r in cp["reviewFiles"]
                 if int(re.search(r"targets_(\d+)", r["path"])[1]) <= 34}
        files = [r for r in cp["reviewFiles"] if r["path"] in prior]
        bindings = [r for r in cp["recordedBindings"] if r["reviewFile"] in prior]
        self.assertEqual(len(files), 208)
        self.assertEqual(len(bindings), 4131)
        self.assertEqual(holds.checkpoint._digest(holds.checkpoint._encoded(files)), "44b7efbb1557522d7164ce8d70533fee4d92fa988c02d6b4f98682f0c16abcc4")
        self.assertEqual(holds.checkpoint._digest(holds.checkpoint._encoded(bindings)), "389e580c8cea59a99db7ff6bdd1ac6e447cc783489f8e2ce97298e3f815729bd")

    def test_original_loader_preserves_all_records_for_audit_and_collision_detection(self):
        recorded = targets.load_reviews()
        self.assertGreaterEqual(len(recorded), 4131)
        for row in self.rows:
            self.assertEqual(recorded[row["reviewTargetId"]]["fdcId"], row["fdcId"])

    def test_shared_profile_gate_rejects_every_held_member_with_or_without_tags(self):
        for row in self.rows:
            for member in row["memberIngredientIds"]:
                for tagged in (False, True):
                    with self.subTest(member=member, tagged=tagged):
                        self.assertFalse(provenance.is_reviewed_profile(
                            old_profile(row, member, tagged=tagged), ingredient_id=member
                        ))

    def test_each_explicit_profile_target_field_enforces_hold(self):
        for field in ("nutritionReviewTargetId", "semanticConceptId", "conceptId", "reviewTargetId"):
            value = old_profile(self.powder, "local:xx:unseen", tagged=False)
            value[field] = self.powder["reviewTargetId"]
            with self.subTest(field=field):
                self.assertFalse(provenance.is_reviewed_profile(value, ingredient_id="local:xx:unseen"))

    def test_no_name_or_global_fdc_id_based_blocking(self):
        value = old_profile(self.powder, "M_FOOD_UNHELD", tagged=False)
        self.assertIsNone(holds.find_hold(self.powder["canonicalEnglishName"], self.powder["fdcId"]))
        self.assertTrue(provenance.is_reviewed_profile(value, ingredient_id="M_FOOD_UNHELD"))

    def test_target_resolver_keeps_all_held_targets_pending_without_fetching(self):
        queue = held_queue(self.rows)
        cache = {m: old_profile(r, m, tagged=False) for r in self.rows for m in r["memberIngredientIds"]}
        before = deepcopy((queue, cache))
        fetch = unittest.mock.Mock(side_effect=AssertionError("must not fetch held binding"))
        output, report = targets.resolve(queue, cache, targets.load_reviews(), fetcher=fetch)
        self.assertEqual(output, {})
        self.assertEqual(report["summary"]["heldReviewTargets"], 12)
        self.assertEqual(report["summary"]["heldIdentities"], 22)
        self.assertEqual(report["summary"]["pendingReviewTargetCount"], 12)
        self.assertEqual(report["summary"]["pendingIdentityCount"], 22)
        self.assertEqual(report["summary"]["rejectedHeldCacheCount"], 22)
        self.assertEqual(report["summary"]["resolvedNowReviewTargets"], 0)
        self.assertTrue(all(r["nutritionReviewStatus"] == "held" for r in report["pending"]))
        fetch.assert_not_called()
        self.assertEqual((queue, cache), before)

    def test_new_unlisted_member_of_held_target_is_still_blocked(self):
        queue = held_queue([self.powder])
        queue["targets"][0]["memberIngredientIds"] = ["local:xx:future-member"]
        cache = {"local:xx:future-member": old_profile(self.powder, "local:xx:future-member", tagged=False)}
        output, report = targets.resolve(queue, cache, {}, fetcher=lambda _: self.fail("fetched"))
        self.assertEqual(output, {})
        self.assertEqual(report["summary"]["heldIdentities"], 1)
        self.assertEqual(report["summary"]["rejectedHeldCacheCount"], 1)

    def test_held_cache_outside_current_queue_is_removed(self):
        queue = held_queue([])
        member = self.powder["memberIngredientIds"][0]
        cache = {member: old_profile(self.powder, member, tagged=False),
                 "unrelated": {"nested": [1]}}
        output, report = targets.resolve(queue, cache, {}, fetcher=lambda _: self.fail("fetched"))
        self.assertNotIn(member, output)
        self.assertEqual(report["summary"]["rejectedHeldCacheCount"], 1)
        output["unrelated"]["nested"].append(2)
        self.assertEqual(cache["unrelated"], {"nested": [1]})

    def test_offline_resolver_never_reads_held_fdc_food_or_metadata(self):
        reference = unittest.mock.Mock()
        reference.manifest_sha256 = self.registry["referenceManifestSha256"]
        output, report = offline.resolve_offline(held_queue([self.powder]), {}, targets.load_reviews(), reference)
        self.assertEqual(output, {})
        self.assertEqual(report["summary"]["heldReviewTargets"], 1)
        reference.food.assert_not_called()
        reference.metadata.assert_not_called()

    def test_exact_identity_resolver_cannot_bypass_target_holds(self):
        queue = target_fixtures.queue()
        queue["tasks"] = [{"ingredientId": m, "canonicalEnglishName": r["canonicalEnglishName"],
                           "identityKind": "source-local" if m.startswith("local:") else "provider",
                           "conceptId": r["reviewTargetId"]}
                          for r in self.rows for m in r["memberIngredientIds"]]
        cache = {m: old_profile(r, m, tagged=False) for r in self.rows for m in r["memberIngredientIds"]}
        output, report = exact.resolve(queue, cache, {}, fetcher=lambda _: self.fail("fetched"))
        self.assertEqual(output, {})
        self.assertEqual(report["summary"]["heldIdentities"], 22)
        self.assertEqual(report["summary"]["pendingCount"], 22)

    def test_finalizer_strips_held_embedded_and_cached_profiles_and_rebuilds_vectors(self):
        for hold in (self.powder, self.blend):
            with self.subTest(target=hold["reviewTargetId"]):
                payload = finalizer_fixtures.payload()
                member = hold["memberIngredientIds"][0]
                ingredient = payload["ingredients"][1]
                ingredient.update(id=member, conceptId=hold["reviewTargetId"], canonicalName=hold["canonicalEnglishName"])
                ingredient["nutrition"] = old_profile(hold, member, tagged=False)
                variant = payload["recipes"][0]["variants"][0]
                variant["ingredients"][1].update(ingredientId=member, conceptId=hold["reviewTargetId"])
                variant["calculatedNutritionV60"] = {"fullyCovered": True, "totals": {"energyKcal": 999}}
                before = deepcopy(payload)
                result = finalizer_fixtures.builder.apply_reviewed_nutrition(payload, {member: ingredient["nutrition"]})
                self.assertNotIn("nutrition", result["ingredients"][1])
                self.assertFalse(result["source"]["reviewedNutritionComplete"])
                self.assertEqual(result["source"]["reviewedNutritionResolvedCount"], 0)
                self.assertFalse(result["recipes"][0]["variants"][0]["calculatedNutritionV60"]["fullyCovered"])
                self.assertEqual(payload, before)
                queue, summary = queue_tool.snapshot(before, {member: ingredient["nutrition"]})
                self.assertIn(member, {r["ingredientId"] for r in queue["tasks"]})

    def test_independent_validator_rejects_held_profiles_even_in_maintenance_mode(self):
        for strict in (False, True):
            value = validator_fixtures.base_catalog()
            value["ingredients"][0]["nutrition"]["nutritionReviewTargetId"] = self.powder["reviewTargetId"]
            result = validator_fixtures.validator.validate(value, require_complete=strict, require_intelligence=strict)
            self.assertFalse(result["valid"])
            self.assertTrue(any("held nutrition binding" in e for e in result["errors"]))

    def test_validator_rejects_held_member_even_after_target_tags_are_stripped(self):
        value = validator_fixtures.base_catalog()
        row = value["ingredients"][1]
        row["id"] = self.powder["memberIngredientIds"][0]
        row["conceptId"] = self.powder["reviewTargetId"]
        result = validator_fixtures.validator.validate(value)
        self.assertFalse(result["valid"])
        self.assertTrue(any("held nutrition binding" in e for e in result["errors"]))

    def test_reuse_proposal_excludes_held_history_but_preserves_recorded_id_skip(self):
        row = self.powder
        evidence = reuse_fixtures._candidate_payload([
            reuse_fixtures._target("M_NEW", row["canonicalEnglishName"], fdc_id=row["fdcId"]),
            reuse_fixtures._target(row["reviewTargetId"], row["canonicalEnglishName"], fdc_id=row["fdcId"]),
        ])
        result, summary = reuse_fixtures.proposal.propose(evidence, {row["reviewTargetId"]: row})
        self.assertEqual(result["proposals"], [])
        self.assertEqual(summary["heldHistoricalReviewsExcluded"], 1)
        self.assertEqual(summary["alreadyReviewedTargetSkipped"], 1)

    def test_missing_registry_and_symlink_fail_closed(self):
        with self.assertRaises(ValueError):
            holds.load_holds(self.path)
        self.path.symlink_to(holds.REGISTRY)
        with self.assertRaises(ValueError):
            holds.load_holds(self.path)

    def test_duplicate_json_keys_and_nonfinite_numbers_fail_closed(self):
        for raw in ('{"kind":"a","kind":"b"}', '{"schemaVersion":NaN}'):
            self.path.write_text(raw)
            with self.assertRaises(ValueError):
                holds.load_holds(self.path)

    def test_schema_kind_policy_and_empty_items_fail_closed(self):
        original = deepcopy(self.registry)
        for key, bad in (("schemaVersion", True), ("kind", "other"), ("items", []), ("policy", {})):
            self.registry = {**deepcopy(original), key: bad}
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load()
        self.registry = original
        self.registry["policy"]["replacementBindingsApproved"] = 0
        with self.assertRaises(ValueError):
            self.load()

    def test_duplicate_hold_and_unsupported_status_fail_closed(self):
        self.registry["items"].append(deepcopy(self.registry["items"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.load()
        self.registry["items"].pop()
        self.registry["items"][0]["status"] = "approved"
        with self.assertRaisesRegex(ValueError, "status"):
            self.load()

    def test_pinned_binding_source_metadata_and_reference_drift_fail_closed(self):
        original = deepcopy(self.registry)
        for key in holds.PINNED_FIELDS:
            self.registry = deepcopy(original)
            self.registry["items"][0][key] = 999 if key in ("fdcId", "candidateEvidenceRank") else "changed"
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load()
        for key in ("referenceManifestSha256", "catalogVersion", "evidenceSha256"):
            self.registry = deepcopy(original)
            self.registry[key] = "changed"
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.load()

    def test_provider_member_cannot_be_grouped_or_renamed(self):
        self.registry["items"][0]["memberIngredientIds"] = ["M_OTHER"]
        with self.assertRaisesRegex(ValueError, "provider hold"):
            self.load()

    def test_semantic_membership_must_be_proven_by_compiled_source_reviews(self):
        row = next(r for r in self.registry["items"] if r["reviewTargetKind"] == "semantic-concept")
        row["memberIngredientIds"] = ["local:xx:invented"]
        with self.assertRaisesRegex(ValueError, "membership drift"):
            self.load()

    def test_source_byte_change_is_not_silently_accepted(self):
        row = self.registry["items"][0]
        self.registry["items"] = [row]
        review_root = self.root / "tools"
        review_root.mkdir()
        source = holds.TOOLS / row["reviewFile"]
        (review_root / source.name).write_bytes(source.read_bytes() + b"\n")
        self.path.write_text(json.dumps(self.registry))
        with self.assertRaisesRegex(ValueError, "source drift"):
            holds.load_holds(self.path, review_root)

    def test_audit_refuses_different_evidence_bytes_without_rewriting_anything(self):
        evidence = evidence_fixture()
        path = self.root / "evidence.json"
        path.write_text(json.dumps(evidence))
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "exact retained candidate snapshot"):
            holds.audit(path)
        self.assertEqual(path.read_bytes(), before)

    def test_compact_retained_evidence_fixture_preserves_all_eleven_discrepancies(self):
        # A subset is evidence for these targets, NOT the original full snapshot.
        path = self.root / "evidence.json"
        path.write_bytes(holds.checkpoint._encoded(evidence_fixture()))
        cp = holds.checkpoint.build_checkpoint(holds.TOOLS)
        resume = holds.checkpoint.reconcile_evidence(cp, path)
        self.assertEqual(resume["summary"]["evidenceTargetCount"], 12)
        self.assertEqual(resume["summary"]["provenanceMismatchCount"], 11)
        self.assertFalse(resume["readyForManualReview"])
        self.assertTrue(all(r["reviewTargetId"] in self.index["targets"] for r in resume["provenanceMismatches"]))

    def test_scoped_review_gate_preserves_raw_findings_and_does_not_approve_holds(self):
        value = evidence_fixture()
        unheld = deepcopy(value["items"][0])
        unheld["reviewTargetId"] = "M_UNREVIEWED_TEST"
        unheld["reviewTargetKind"] = "provider-identity"
        value["items"].append(unheld)
        path = self.root / "evidence.json"
        path.write_bytes(holds.checkpoint._encoded(value))
        self.registry["evidenceSha256"] = holds.checkpoint._digest(path.read_bytes())
        self.path.write_bytes(holds.checkpoint._encoded(self.registry))
        result = holds.audit(path, registry_path=self.path)
        self.assertEqual(result["summary"]["provenanceMismatchCount"], 11)
        self.assertEqual(result["summary"]["unheldProvenanceMismatchCount"], 0)
        self.assertFalse(result["readyForManualReview"])
        self.assertTrue(result["readyForUnheldManualReview"])
        self.assertFalse(result["catalogNutritionApprovalGranted"])
        self.assertFalse(result["semanticApprovalPerformed"])
        self.assertFalse(result["selectionPerformed"])
        self.assertEqual(result["remainingUnheldCandidates"], [unheld])
        self.assertEqual(result["summary"]["unresolvedOrHeldEvidenceTargetCount"], 13)

    def test_unknown_unheld_discrepancy_still_blocks_scoped_review(self):
        value = evidence_fixture()
        cp = holds.checkpoint.build_checkpoint(holds.TOOLS)
        record = next(r for r in cp["recordedBindings"] if r["reviewTargetId"] not in self.index["targets"])
        extra = {**record, "canonicalEnglishName": record["canonicalEnglishName"] + " changed",
                 "candidates": []}
        value["items"].append(extra)
        path = self.root / "evidence.json"
        path.write_bytes(holds.checkpoint._encoded(value))
        self.registry["evidenceSha256"] = holds.checkpoint._digest(path.read_bytes())
        self.path.write_bytes(holds.checkpoint._encoded(self.registry))
        result = holds.audit(path, registry_path=self.path)
        self.assertFalse(result["readyForUnheldManualReview"])
        self.assertEqual(result["summary"]["unheldProvenanceMismatchCount"], 1)


if __name__ == "__main__":
    unittest.main()
