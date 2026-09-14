from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import compile_release_catalog_semantics_v60 as semantics  # noqa: E402
import snapshot_release_catalog_review_queues_v60 as queue  # noqa: E402


def local_row(language: str, source: str, **extra) -> dict:
    ident = semantics.source_local_ingredient_id(language, source)
    row = {
        "id": ident,
        "key": "",
        "canonicalName": source,
        "translations": {language: source},
        "sourceLocalIdentity": True,
        "providerIdentityAssigned": False,
        "conceptId": "",
        "classification": "ambiguous",
        "confidence": "unreviewed",
        "canonicalEnglishNeedsReview": True,
    }
    row.update(extra)
    return row


def fixture() -> dict:
    new_local = local_row("de", "Neue Zutat")
    reviewed_local = local_row(
        "fr",
        "fragment revu",
        conceptId="concept:source:reviewed",
        classification="ambiguous",
        confidence="medium",
        canonicalEnglishNeedsReview=False,
    )
    return {
        "schemaVersion": 1,
        "catalogVersion": "capture-test",
        "ingredients": [
            new_local,
            reviewed_local,
            {
                "id": "M_FOOD_9999",
                "key": "M_FOOD_9999",
                "canonicalName": "Ingrediente prova",
                "canonicalNameSourceLanguage": "it",
                "canonicalEnglishNeedsReview": True,
                "translations": {"it": "Ingrediente prova", "es": "Ingrediente prueba"},
            },
            {
                "id": "M_FOOD_1",
                "key": "M_FOOD_1",
                "canonicalName": "Water",
                "translations": {"en": "Water"},
            },
        ],
        "recipes": [
            {
                "groupingFunctionalId": "G1",
                "variants": [
                    {
                        "variantId": "V1",
                        "originalLanguage": "de",
                        "title": "SECRET TITLE MUST NOT ENTER QUEUE",
                        "ingredients": [
                            {"ingredientId": new_local["id"], "quantity": 1},
                            {"ingredientId": "M_FOOD_9999", "key": "M_FOOD_9999"},
                        ],
                    },
                    {
                        "variantId": "V2",
                        "originalLanguage": "de",
                        "ingredients": [
                            {"ingredientId": new_local["id"]},
                        ],
                    },
                ],
            },
            {
                "groupingFunctionalId": "G2",
                "variants": [
                    {
                        "variantId": "V3",
                        "originalLanguage": "it",
                        "ingredients": [
                            {"ingredientId": "M_FOOD_9999", "key": "M_FOOD_9999"},
                        ],
                    }
                ],
            },
        ],
    }


class ReviewQueueSnapshotV60Tests(unittest.TestCase):
    def test_exact_unreviewed_source_and_provider_rows_are_queued(self):
        value = queue.snapshot(fixture(), example_limit=3)
        self.assertEqual(value["kind"], "cook4me-v60-review-queues")
        self.assertEqual(value["catalogVersion"], "capture-test")
        self.assertEqual(value["summary"]["sourceLocalSemanticReviewCount"], 1)
        self.assertEqual(value["summary"]["providerCanonicalEnglishReviewCount"], 1)
        self.assertEqual(value["summary"]["sourceLocalByLanguage"], {"de": 1})

        semantic = value["sourceLocalSemanticReview"][0]
        self.assertEqual(semantic["language"], "de")
        self.assertEqual(semantic["source"], "Neue Zutat")
        self.assertEqual(
            semantic["ingredientId"],
            semantics.source_local_ingredient_id("de", "Neue Zutat"),
        )
        self.assertEqual(semantic["usageCount"], 2)
        self.assertEqual(
            [row["variantId"] for row in semantic["examples"]],
            ["V1", "V2"],
        )

        provider = value["providerCanonicalEnglishReview"][0]
        self.assertEqual(provider["ingredientId"], "M_FOOD_9999")
        self.assertEqual(provider["providerKey"], "M_FOOD_9999")
        self.assertEqual(provider["fallbackCanonicalName"], "Ingrediente prova")
        self.assertEqual(provider["fallbackSourceLanguage"], "it")
        self.assertEqual(
            provider["translations"],
            {"es": "Ingrediente prueba", "it": "Ingrediente prova"},
        )
        self.assertEqual(provider["usageCount"], 2)

    def test_reviewed_ambiguous_and_resolved_provider_rows_are_not_requeued(self):
        value = queue.snapshot(fixture())
        ids = {
            row["ingredientId"] for row in value["sourceLocalSemanticReview"]
        } | {
            row["ingredientId"] for row in value["providerCanonicalEnglishReview"]
        }
        self.assertNotIn(
            semantics.source_local_ingredient_id("fr", "fragment revu"), ids
        )
        self.assertNotIn("M_FOOD_1", ids)

    def test_source_local_identity_must_match_exact_source_label(self):
        payload = fixture()
        row = payload["ingredients"][0]
        row["translations"]["de"] = "Andere Zutat"
        with self.assertRaisesRegex(RuntimeError, "identity/source mismatch"):
            queue.snapshot(payload)

    def test_provider_review_row_must_preserve_exact_key(self):
        payload = fixture()
        payload["ingredients"][2]["key"] = "M_FOOD_DIFFERENT"
        with self.assertRaisesRegex(RuntimeError, "exact provider identity"):
            queue.snapshot(payload)

    def test_output_is_bounded_and_contains_no_generated_review_decisions(self):
        value = queue.snapshot(fixture(), example_limit=1)
        self.assertEqual(value["policy"]["exampleLimit"], 1)
        self.assertFalse(value["policy"]["translationsGenerated"])
        self.assertFalse(value["policy"]["classificationsGenerated"])
        self.assertFalse(value["policy"]["reviewDecisionsGenerated"])
        self.assertEqual(len(value["sourceLocalSemanticReview"][0]["examples"]), 1)
        rendered = str(value)
        self.assertNotIn("SECRET TITLE MUST NOT ENTER QUEUE", rendered)
        for row in value["sourceLocalSemanticReview"]:
            self.assertNotIn("english", row)
            self.assertNotIn("classification", row)
            self.assertNotIn("confidence", row)

    def test_snapshot_is_deterministic_and_does_not_mutate_capture(self):
        payload = fixture()
        before = deepcopy(payload)
        one = queue.snapshot(payload, example_limit=2)
        two = queue.snapshot(payload, example_limit=2)
        self.assertEqual(one, two)
        self.assertEqual(payload, before)

    def test_queue_order_is_usage_first_then_identity(self):
        payload = fixture()
        second = local_row("es", "Ingrediente nueva")
        payload["ingredients"].append(second)
        payload["recipes"][0]["variants"][0]["ingredients"].append(
            {"ingredientId": second["id"]}
        )
        value = queue.snapshot(payload)
        self.assertEqual(
            [row["usageCount"] for row in value["sourceLocalSemanticReview"]],
            [2, 1],
        )


if __name__ == "__main__":
    unittest.main()
