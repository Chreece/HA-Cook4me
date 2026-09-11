from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
for path in (ROOT, TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import compile_release_catalog_semantics_v60 as semantics  # noqa: E402
import reconcile_release_catalog_review_queues_v60 as reconcile  # noqa: E402
import release_catalog_canonical_reviews_v60 as canonical_reviews  # noqa: E402

CATALOG_VERSION = "2026-09-11-v60-capture3"
SOURCE_QUEUE_SHA256 = "326d9bc76a27220e1c60653b96689cc9fa414af9ab0a746d4090c6425ac4fd6c"
SOURCE_ID_SET_SHA256 = "f656f4dc8fc6655bbeedeaa9a506efd2df1b5f7fba86f30f586263b72ff36ed8"
PROVIDER_ID_SET_SHA256 = "229273ade7ca2eb7e8c1cf54cb2c87755945965c5a136ad6790486ac8c689d1e"
EXPECTED_LANGUAGE_COUNTS = {
    "ar": 74,
    "bg": 144,
    "cs": 32,
    "de": 19,
    "en": 26,
    "es": 35,
    "fr": 5,
    "hr": 169,
    "hu": 36,
    "it": 79,
    "ja": 57,
    "ko": 49,
    "pl": 13,
    "pt": 87,
    "ro": 34,
    "ru": 48,
    "sk": 29,
    "sl": 1,
    "tr": 93,
    "uk": 149,
    "zh": 34,
}
PROVIDER_QUEUE_IDS = set("""
M_FOOD_101 M_FOOD_103 M_FOOD_106 M_FOOD_110 M_FOOD_121 M_FOOD_124 M_FOOD_127 M_FOOD_128 M_FOOD_133 M_FOOD_135 M_FOOD_136 M_FOOD_14
M_FOOD_140 M_FOOD_141 M_FOOD_142 M_FOOD_143 M_FOOD_145 M_FOOD_148 M_FOOD_15 M_FOOD_152 M_FOOD_153 M_FOOD_157 M_FOOD_168 M_FOOD_17
M_FOOD_173 M_FOOD_174 M_FOOD_175 M_FOOD_178 M_FOOD_179 M_FOOD_18 M_FOOD_180 M_FOOD_181 M_FOOD_182 M_FOOD_184 M_FOOD_189 M_FOOD_195
M_FOOD_198 M_FOOD_200 M_FOOD_204 M_FOOD_206 M_FOOD_208 M_FOOD_212 M_FOOD_218 M_FOOD_222 M_FOOD_224 M_FOOD_228 M_FOOD_229 M_FOOD_234
M_FOOD_236 M_FOOD_239 M_FOOD_240 M_FOOD_241 M_FOOD_248 M_FOOD_249 M_FOOD_251 M_FOOD_253 M_FOOD_254 M_FOOD_260 M_FOOD_262 M_FOOD_265
M_FOOD_266 M_FOOD_273 M_FOOD_28 M_FOOD_281 M_FOOD_282 M_FOOD_283 M_FOOD_285 M_FOOD_288 M_FOOD_290 M_FOOD_294 M_FOOD_295 M_FOOD_299
M_FOOD_311 M_FOOD_312 M_FOOD_314 M_FOOD_317 M_FOOD_318 M_FOOD_320 M_FOOD_326 M_FOOD_330 M_FOOD_333 M_FOOD_335 M_FOOD_339 M_FOOD_342
M_FOOD_362 M_FOOD_365 M_FOOD_368 M_FOOD_37 M_FOOD_372 M_FOOD_373 M_FOOD_376 M_FOOD_379 M_FOOD_381 M_FOOD_397 M_FOOD_401 M_FOOD_403
M_FOOD_405 M_FOOD_411 M_FOOD_417 M_FOOD_420 M_FOOD_423 M_FOOD_424 M_FOOD_426 M_FOOD_429 M_FOOD_430 M_FOOD_431 M_FOOD_439 M_FOOD_441
M_FOOD_447 M_FOOD_450 M_FOOD_452 M_FOOD_456 M_FOOD_459 M_FOOD_463 M_FOOD_464 M_FOOD_468 M_FOOD_47 M_FOOD_471 M_FOOD_472 M_FOOD_474
M_FOOD_48 M_FOOD_481 M_FOOD_482 M_FOOD_488 M_FOOD_5 M_FOOD_502 M_FOOD_506 M_FOOD_509 M_FOOD_512 M_FOOD_515 M_FOOD_516 M_FOOD_520
M_FOOD_522 M_FOOD_523 M_FOOD_524 M_FOOD_525 M_FOOD_526 M_FOOD_533 M_FOOD_534 M_FOOD_536 M_FOOD_538 M_FOOD_539 M_FOOD_540 M_FOOD_541
M_FOOD_542 M_FOOD_543 M_FOOD_545 M_FOOD_548 M_FOOD_551 M_FOOD_554 M_FOOD_555 M_FOOD_556 M_FOOD_557 M_FOOD_558 M_FOOD_561 M_FOOD_562
M_FOOD_563 M_FOOD_568 M_FOOD_569 M_FOOD_57 M_FOOD_571 M_FOOD_573 M_FOOD_581 M_FOOD_582 M_FOOD_583 M_FOOD_584 M_FOOD_585 M_FOOD_586
M_FOOD_587 M_FOOD_588 M_FOOD_591 M_FOOD_592 M_FOOD_593 M_FOOD_594 M_FOOD_596 M_FOOD_597 M_FOOD_599 M_FOOD_600 M_FOOD_602 M_FOOD_604
M_FOOD_606 M_FOOD_607 M_FOOD_61 M_FOOD_611 M_FOOD_612 M_FOOD_613 M_FOOD_615 M_FOOD_616 M_FOOD_619 M_FOOD_62 M_FOOD_622 M_FOOD_623
M_FOOD_624 M_FOOD_625 M_FOOD_627 M_FOOD_628 M_FOOD_629 M_FOOD_631 M_FOOD_632 M_FOOD_633 M_FOOD_634 M_FOOD_636 M_FOOD_637 M_FOOD_638
M_FOOD_64 M_FOOD_640 M_FOOD_641 M_FOOD_642 M_FOOD_643 M_FOOD_644 M_FOOD_645 M_FOOD_646 M_FOOD_647 M_FOOD_648 M_FOOD_650 M_FOOD_651
M_FOOD_652 M_FOOD_653 M_FOOD_659 M_FOOD_661 M_FOOD_662 M_FOOD_667 M_FOOD_668 M_FOOD_669 M_FOOD_67 M_FOOD_670 M_FOOD_673 M_FOOD_675
M_FOOD_676 M_FOOD_680 M_FOOD_683 M_FOOD_684 M_FOOD_688 M_FOOD_692 M_FOOD_694 M_FOOD_696 M_FOOD_697 M_FOOD_699 M_FOOD_70 M_FOOD_700
M_FOOD_703 M_FOOD_705 M_FOOD_707 M_FOOD_708 M_FOOD_71 M_FOOD_712 M_FOOD_719 M_FOOD_72 M_FOOD_724 M_FOOD_727 M_FOOD_729 M_FOOD_73
M_FOOD_730 M_FOOD_732 M_FOOD_733 M_FOOD_734 M_FOOD_735 M_FOOD_738 M_FOOD_74 M_FOOD_740 M_FOOD_741 M_FOOD_743 M_FOOD_744 M_FOOD_746
M_FOOD_748 M_FOOD_749 M_FOOD_751 M_FOOD_756 M_FOOD_757 M_FOOD_758 M_FOOD_760 M_FOOD_761 M_FOOD_762 M_FOOD_764 M_FOOD_765 M_FOOD_766
M_FOOD_768 M_FOOD_769 M_FOOD_770 M_FOOD_771 M_FOOD_772 M_FOOD_773 M_FOOD_774 M_FOOD_778 M_FOOD_779 M_FOOD_780 M_FOOD_782 M_FOOD_783
M_FOOD_789 M_FOOD_790 M_FOOD_791 M_FOOD_792 M_FOOD_793 M_FOOD_795 M_FOOD_798 M_FOOD_799 M_FOOD_8 M_FOOD_80 M_FOOD_800 M_FOOD_802
M_FOOD_805 M_FOOD_807 M_FOOD_808 M_FOOD_809 M_FOOD_810 M_FOOD_811 M_FOOD_86 M_FOOD_9 M_FOOD_91 M_FOOD_96 M_FOOD_97
""".split())


def _digest(values: list[str] | set[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode()).hexdigest()


def _capture3_review_rows() -> tuple[list[dict], dict[str, int]]:
    rows: list[dict] = []
    counts: Counter[str] = Counter()
    paths = sorted(TOOLS.glob("release_catalog_reviewed_keyless_ingredients_capture3_*_001.v1.json"))
    if len(paths) != 21:
        raise AssertionError(f"expected 21 Capture 3 review files, got {len(paths)}")
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("policy", {}).get("catalogVersion") != CATALOG_VERSION:
            raise AssertionError(f"wrong catalog version in {path.name}")
        for row in payload.get("items") or []:
            language = str(row["language"]).strip().lower()
            source = str(row["source"]).strip()
            ident = semantics.source_local_ingredient_id(language, source)
            rows.append(
                {
                    "ingredientId": ident,
                    "language": language,
                    "source": source,
                    "usageCount": 1,
                    "examples": [],
                }
            )
            counts[language] += 1
    return rows, dict(sorted(counts.items()))


class Capture3FinalReviewReconciliationV60Tests(unittest.TestCase):
    def test_original_capture3_source_identity_set_is_fully_committed(self):
        rows, counts = _capture3_review_rows()
        ids = [row["ingredientId"] for row in rows]
        self.assertEqual(len(rows), 1213)
        self.assertEqual(len(set(ids)), 1213)
        self.assertEqual(counts, EXPECTED_LANGUAGE_COUNTS)
        self.assertEqual(_digest(ids), SOURCE_ID_SET_SHA256)

    def test_original_provider_queue_identity_set_is_still_exact_and_untouched(self):
        self.assertEqual(len(PROVIDER_QUEUE_IDS), 311)
        self.assertEqual(_digest(PROVIDER_QUEUE_IDS), PROVIDER_ID_SET_SHA256)
        committed = canonical_reviews._provider_food_reviews(TOOLS)
        self.assertEqual(len(committed), 109)
        self.assertTrue(PROVIDER_QUEUE_IDS.isdisjoint(committed))

    def test_exact_reconciliation_is_1213_complete_and_311_provider_pending(self):
        semantic_rows, counts = _capture3_review_rows()
        provider_rows = [
            {
                "ingredientId": ident,
                "providerKey": ident,
            }
            for ident in sorted(PROVIDER_QUEUE_IDS)
        ]
        queue = {
            "schemaVersion": 1,
            "kind": "cook4me-v60-review-queues",
            "catalogVersion": CATALOG_VERSION,
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
                "sourceLocalSemanticReviewCount": 1213,
                "providerCanonicalEnglishReviewCount": 311,
                "sourceLocalByLanguage": counts,
            },
            "sourceLocalSemanticReview": semantic_rows,
            "providerCanonicalEnglishReview": provider_rows,
        }
        value = reconcile.reconcile(queue, tools_dir=TOOLS)
        self.assertEqual(value["summary"]["queuedSourceLocalSemanticReviewCount"], 1213)
        self.assertEqual(value["summary"]["alreadyReviewedSourceLocalExactCount"], 1213)
        self.assertEqual(value["summary"]["needsSourceLocalSemanticReviewCount"], 0)
        self.assertEqual(value["summary"]["needsSourceLocalByLanguage"], {})
        self.assertEqual(value["summary"]["queuedProviderCanonicalEnglishReviewCount"], 311)
        self.assertEqual(value["summary"]["alreadyReviewedProviderCanonicalExactCount"], 0)
        self.assertEqual(value["summary"]["needsProviderCanonicalEnglishReviewCount"], 311)
        self.assertEqual(value["reviewCorpus"]["reviewedSourceLabelCount"], 10994)
        self.assertEqual(value["reviewCorpus"]["providerCanonicalEnglishReviewCount"], 109)

    def test_original_queue_provenance_is_locked(self):
        self.assertEqual(
            SOURCE_QUEUE_SHA256,
            "326d9bc76a27220e1c60653b96689cc9fa414af9ab0a746d4090c6425ac4fd6c",
        )


if __name__ == "__main__":
    unittest.main()
