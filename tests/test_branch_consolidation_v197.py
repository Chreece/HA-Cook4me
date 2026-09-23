from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

class ConsolidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / "custom_components/cook4me/catalog/merged_catalog.v1.json").read_bytes())
        cls.baseline = json.loads((ROOT / "tests/fixtures/consolidation-baseline-v197.json").read_text())
        cls.report = json.loads((ROOT / "docs/CATALOG_RECONCILIATION_V197.json").read_text())

    def test_recipes_and_variant_instructions_unchanged(self):
        self.assertEqual(digest(self.catalog["recipes"]), self.baseline["recipesSha256"])

    def test_all_original_ingredient_ids_remain(self):
        ids = [r["id"] for r in self.catalog["ingredients"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(digest(sorted(ids)), self.baseline["ingredientIdsSha256"])

    def test_retained_profiles_are_exact_id_bound(self):
        for row in self.catalog["ingredients"]:
            if row.get("nutrition"):
                self.assertEqual(row["nutrition"]["ingredientId"], row["id"])

    def test_unsafe_semantic_closure_does_not_authorize_nutrition(self):
        for row in self.catalog["ingredients"]:
            if row.get("needsSemanticConfirmation") or row.get("nutritionEligible") is False:
                self.assertFalse(row.get("nutrition"), row["id"])

    def test_unresolved_profiles_are_explicit_not_filled(self):
        self.assertFalse(self.catalog["source"].get("ingredientIntelligenceComplete"))
        self.assertTrue(self.report["removedIneligibleOrUnprovenProfiles"])
        present = {r["id"] for r in self.catalog["ingredients"] if r.get("nutrition")}
        self.assertFalse(present.intersection(self.report["removedIneligibleOrUnprovenProfiles"]))

    def test_audit_has_no_duplicate_or_missing_branch_tip(self):
        audit = json.loads((ROOT / "docs/BRANCH_CONSOLIDATION_V197.json").read_text())
        rows = audit["branches"]
        self.assertEqual(len(rows), audit["originalBranchCount"])
        self.assertEqual(len(rows), len({r["branch"] for r in rows}))
        self.assertEqual(sum(r["branch"] == "main" for r in rows), 1)
        for row in rows:
            self.assertRegex(row["sha"], r"^[0-9a-f]{40}$")
            self.assertTrue(row["resolution"])

    def test_semantic_alias_order_does_not_depend_on_python_hash_seed(self):
        program = (
            "import hashlib,json,sys;sys.path.insert(0,'tools');"
            "import compile_release_catalog_semantics_v60 as s;"
            "value=s.compile_from_paths(s._review_paths());"
            "print(hashlib.sha256(json.dumps(value,sort_keys=True,"
            "ensure_ascii=False,separators=(',',':')).encode()).hexdigest())"
        )
        results = []
        for seed in ("1", "42"):
            results.append(subprocess.check_output(
                [sys.executable, "-c", program], cwd=ROOT,
                env={**os.environ, "PYTHONHASHSEED": seed}, text=True,
                timeout=120,
            ).strip())
        self.assertEqual(results[0], results[1])

    def test_obsolete_writing_workflows_not_reactivated(self):
        paths = {p.name for p in (ROOT / ".github/workflows").glob("*.yml")}
        self.assertNotIn("catalog-semantic-confirmation-apply-v60.yml", paths)
        self.assertNotIn("batch41-discover.yml", paths)
        self.assertNotIn("catalog-post-activation-nutrition-activate-v60.yml", paths)

if __name__ == "__main__":
    unittest.main()
