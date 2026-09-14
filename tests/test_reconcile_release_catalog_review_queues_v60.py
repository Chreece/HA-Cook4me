from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import compile_release_catalog_semantics_v60 as semantics  # noqa: E402
import reconcile_release_catalog_review_queues_v60 as reconcile  # noqa: E402


def local_queue_row(language: str, source: str, usage: int = 1) -> dict:
    return {
        "ingredientId": semantics.source_local_ingredient_id(language, source),
        "language": language,
        "source": source,
        "usageCount": usage,
        "examples": [],
    }


def provider_queue_row(ident: str, label: str) -> dict:
    return {
        "ingredientId": ident,
        "providerKey": ident,
        "fallbackCanonicalName": label,
        "fallbackSourceLanguage": "it",
        "translations": {"it": label},
        "usageCount": 1,
        "examples": [],
    }


def queue_fixture() -> dict:
    semantic = [
        local_queue_row("de", "Wasser", usage=4),
        local_queue_row("fr", "Nouvel ingrédient", usage=2),
    ]
    providers = [
        provider_queue_row("M_FOOD_1", "Acqua"),
        provider_queue_row("M_FOOD_2", "Ingrediente nuovo"),
    ]
    return {
        "schemaVersion": 1,
        "kind": "cook4me-v60-review-queues",
        "catalogVersion": "capture-test",
        "policy": {
            "offlineOnly": True,
            "capturedCatalogMutated": False,
            "providerIdentityInferred": False,
            "sourceLocalIdentityRecomputed": True,
            "exactSourceLabelOnly": True,
            "translationsGenerated": False,
            "classificationsGenerated": False,
            "reviewDecisionsGenerated": False,
            "exampleLimit": 3,
        },
        "summary": {
            "sourceLocalSemanticReviewCount": len(semantic),
            "providerCanonicalEnglishReviewCount": len(providers),
            "sourceLocalByLanguage": {"de": 1, "fr": 1},
        },
        "sourceLocalSemanticReview": semantic,
        "providerCanonicalEnglishReview": providers,
    }


def write_corpus(root: Path) -> None:
    (root / "release_catalog_reviewed_keyless_ingredients.v1.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "kind": "cook4me-reviewed-keyless-ingredient-semantics",
                "items": [
                    {
                        "language": "de",
                        "source": "Wasser",
                        "english": "Water",
                        "classification": "food",
                        "confidence": "high",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / "release_catalog_reviewed_provider_food_english.v2.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "kind": "cook4me-reviewed-provider-food-english",
                "items": {
                    "M_FOOD_1": {"english": "Water", "confidence": "high"}
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


class ReviewQueueReconciliationV60Tests(unittest.TestCase):
    def run_reconcile(self, payload: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_corpus(root)
            return reconcile.reconcile(payload, tools_dir=root)

    def test_exact_current_reviews_are_separated_from_genuinely_new_rows(self):
        value = self.run_reconcile(queue_fixture())
        self.assertEqual(value["kind"], "cook4me-v60-review-queue-reconciliation")
        self.assertEqual(value["catalogVersion"], "capture-test")
        self.assertEqual(value["summary"]["queuedSourceLocalSemanticReviewCount"], 2)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 1)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 1)
        self.assertEqual(value["summary"]["queuedProviderCanonicalEnglishReviewCount"], 2)
        self.assertEqual(value["summary"]["alreadyReviewedProviderCanonicalExactCount"], 1)
        self.assertEqual(value["summary"]["needsProviderCanonicalEnglishReviewCount"], 1)
        self.assertEqual(value["summary"]["needsSourceLocalByLanguage"], {"fr": 1})

        reviewed = value["alreadyReviewedSourceLocalExact"][0]
        self.assertEqual(reviewed["source"], "Wasser")
        self.assertEqual(reviewed["canonicalEnglish"], "Water")
        self.assertEqual(reviewed["classification"], "food")

        pending = value["needsSourceLocalSemanticReview"][0]
        self.assertEqual(pending["source"], "Nouvel ingrédient")
        self.assertNotIn("english", pending)
        self.assertNotIn("classification", pending)
        self.assertNotIn("confidence", pending)

        provider_reviewed = value["alreadyReviewedProviderCanonicalExact"][0]
        self.assertEqual(provider_reviewed["providerKey"], "M_FOOD_1")
        self.assertEqual(provider_reviewed["english"], "Water")
        self.assertEqual(
            value["needsProviderCanonicalEnglishReview"][0]["providerKey"],
            "M_FOOD_2",
        )

    def test_same_source_text_in_wrong_language_is_not_an_exact_review_match(self):
        payload = queue_fixture()
        payload["sourceLocalSemanticReview"] = [local_queue_row("fr", "Wasser")]
        payload["summary"]["sourceLocalSemanticReviewCount"] = 1
        payload["summary"]["sourceLocalByLanguage"] = {"fr": 1}
        value = self.run_reconcile(payload)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 0)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 1)

    def test_source_local_identity_must_recompute_from_exact_language_and_source(self):
        payload = queue_fixture()
        payload["sourceLocalSemanticReview"][0]["source"] = "Anderes Wasser"
        with self.assertRaisesRegex(RuntimeError, "identity/source mismatch"):
            self.run_reconcile(payload)

    def test_provider_identity_must_equal_exact_provider_key(self):
        payload = queue_fixture()
        payload["providerCanonicalEnglishReview"][0]["providerKey"] = "M_FOOD_OTHER"
        with self.assertRaisesRegex(RuntimeError, "identity/key mismatch"):
            self.run_reconcile(payload)

    def test_duplicate_queue_identities_fail_closed(self):
        payload = queue_fixture()
        payload["sourceLocalSemanticReview"].append(
            deepcopy(payload["sourceLocalSemanticReview"][0])
        )
        payload["summary"]["sourceLocalSemanticReviewCount"] += 1
        payload["summary"]["sourceLocalByLanguage"]["de"] += 1
        with self.assertRaisesRegex(RuntimeError, "duplicate source-local identity"):
            self.run_reconcile(payload)

    def test_queue_summary_and_evidence_policy_are_validated(self):
        payload = queue_fixture()
        payload["summary"]["sourceLocalSemanticReviewCount"] = 99
        with self.assertRaisesRegex(RuntimeError, "count does not match summary"):
            self.run_reconcile(payload)

        payload = queue_fixture()
        payload["policy"]["sourceLocalIdentityRecomputed"] = False
        with self.assertRaisesRegex(RuntimeError, "sourceLocalIdentityRecomputed"):
            self.run_reconcile(payload)

    def test_reconciliation_is_deterministic_and_does_not_generate_decisions(self):
        payload = queue_fixture()
        before = deepcopy(payload)
        one = self.run_reconcile(payload)
        two = self.run_reconcile(payload)
        self.assertEqual(one, two)
        self.assertEqual(payload, before)
        self.assertTrue(one["policy"]["offlineOnly"])
        self.assertFalse(one["policy"]["translationsGenerated"])
        self.assertFalse(one["policy"]["classificationsGenerated"])
        self.assertFalse(one["policy"]["reviewDecisionsGenerated"])
        self.assertFalse(one["policy"]["providerIdentityInferred"])


if __name__ == "__main__":
    unittest.main()
