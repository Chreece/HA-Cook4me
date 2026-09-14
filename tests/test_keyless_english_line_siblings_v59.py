from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
SCRIPT = TOOLS / "probe_keyless_english_line_siblings_v59.py"
spec = importlib.util.spec_from_file_location("probe_keyless_english_line_siblings_v59", SCRIPT)
assert spec and spec.loader
probe = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = probe
spec.loader.exec_module(probe)


def provider(details):
    return {"schemaVersion": 2, "kind": "cook4me-provider-capture", "details": details}


class KeylessEnglishLineSiblingEvidenceTests(unittest.TestCase):
    def test_safe_candidate_requires_same_group_and_line_and_provider_proven_food(self):
        result = probe.analyze(
            provider(
                [
                    {
                        "variantId": "de-v",
                        "groupingFunctionalId": "g1",
                        "language": "de",
                        "ingredients": [{"lineFunctionalId": "line-1", "applicationDescription": "Wasser"}],
                    },
                    {
                        "variantId": "en-v",
                        "groupingFunctionalId": "g1",
                        "language": "en",
                        "ingredients": [{"lineFunctionalId": "line-1", "foodKey": "M_FOOD_WATER", "foodName": "Water"}],
                    },
                ]
            )
        )
        self.assertEqual(1, result["safeCandidateCount"])
        candidate = result["safeCandidates"][0]
        self.assertEqual("de", candidate["sourceLanguage"])
        self.assertEqual("Wasser", candidate["sourceText"])
        self.assertEqual("Water", candidate["canonicalEnglishName"])
        self.assertEqual("food", candidate["classification"])
        self.assertEqual(["M_FOOD_WATER"], candidate["englishSiblingFoodKeys"])

    def test_missing_english_sibling_is_not_safe(self):
        result = probe.analyze(
            provider(
                [
                    {
                        "variantId": "de-v",
                        "groupingFunctionalId": "g1",
                        "language": "de",
                        "ingredients": [{"lineFunctionalId": "line-1", "applicationDescription": "Wasser"}],
                    }
                ]
            )
        )
        self.assertEqual(0, result["safeCandidateCount"])
        self.assertEqual(1, result["unresolvedReasonCounts"]["missing_english_sibling"])

    def test_conflicting_english_sibling_names_are_not_safe(self):
        result = probe.analyze(
            provider(
                [
                    {
                        "variantId": "de-v",
                        "groupingFunctionalId": "g1",
                        "language": "de",
                        "ingredients": [{"lineFunctionalId": "line-1", "applicationDescription": "Sahne"}],
                    },
                    {
                        "variantId": "en-v1",
                        "groupingFunctionalId": "g1",
                        "language": "en",
                        "ingredients": [{"lineFunctionalId": "line-1", "foodKey": "M_FOOD_A", "foodName": "Cream"}],
                    },
                    {
                        "variantId": "en-v2",
                        "groupingFunctionalId": "g1",
                        "language": "en",
                        "ingredients": [{"lineFunctionalId": "line-1", "foodKey": "M_FOOD_B", "foodName": "Sour cream"}],
                    },
                ]
            )
        )
        self.assertEqual(0, result["safeCandidateCount"])
        self.assertEqual(1, result["unresolvedReasonCounts"]["conflicting_english_sibling_names"])

    def test_keyless_english_sibling_without_foodname_is_not_classification_proof(self):
        result = probe.analyze(
            provider(
                [
                    {
                        "variantId": "de-v",
                        "groupingFunctionalId": "g1",
                        "language": "de",
                        "ingredients": [{"lineFunctionalId": "line-1", "applicationDescription": "Folie"}],
                    },
                    {
                        "variantId": "en-v",
                        "groupingFunctionalId": "g1",
                        "language": "en",
                        "ingredients": [{"lineFunctionalId": "line-1", "applicationDescription": "foil"}],
                    },
                ]
            )
        )
        self.assertEqual(0, result["safeCandidateCount"])
        self.assertEqual(1, result["unresolvedReasonCounts"]["english_sibling_not_provider_proven_food"])


if __name__ == "__main__":
    unittest.main()
