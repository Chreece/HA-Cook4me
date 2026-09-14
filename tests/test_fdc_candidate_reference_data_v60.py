from __future__ import annotations

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

import fdc_reference_data_v60 as full_reference  # noqa: E402
import fdc_candidate_reference_data_v60 as candidate_reference  # noqa: E402


class CandidateReferenceIndexTests(unittest.TestCase):
    def _manifest(self, root: Path) -> Path:
        datasets = [
            (
                "Foundation",
                "foundation.json",
                "FoundationFoods",
                [
                    {
                        "fdcId": 101,
                        "description": "Tomato",
                        "foodCategory": {"description": "Vegetables"},
                        "scientificName": "Solanum lycopersicum",
                        "commonNames": "garden tomato",
                        "additionalDescriptions": "fresh whole tomato",
                    },
                    {
                        "fdcId": 102,
                        "description": "Rice, brown",
                        "foodCategory": {"description": "Grains"},
                    },
                    {
                        "fdcId": 103,
                        "description": "Kelp, raw",
                        "foodCategory": {"description": "Sea vegetables"},
                    },
                ],
            ),
            (
                "SR Legacy",
                "legacy.json",
                "SRLegacyFoods",
                [
                    {"fdcId": 201, "description": "Tomatoes, red, ripe, raw"},
                    {
                        "fdcId": 202,
                        "description": "Sugar, brown",
                        "commonNames": "muscovado sugar",
                    },
                    {"fdcId": 203, "description": "Wheat gluten, cooked"},
                    {"fdcId": 204, "description": "Tomato puree, canned"},
                ],
            ),
            (
                "Survey (FNDDS)",
                "survey.json",
                "SurveyFoods",
                [
                    {
                        "fdcId": 301,
                        "description": "Rice with vegetables",
                        "wweiaFoodCategory": {"description": "Mixed dishes"},
                    },
                    {"fdcId": 302, "description": "Rice wine"},
                    {"fdcId": 303, "description": "Red pepper paste"},
                ],
            ),
        ]
        manifest_rows = []
        for data_type, filename, key, rows in datasets:
            (root / filename).write_text(json.dumps({key: rows}), encoding="utf-8")
            manifest_rows.append(
                {
                    "dataType": data_type,
                    "releaseDate": "test",
                    "jsonPath": filename,
                }
            )
        manifest = root / "reference-manifest.v60.json"
        manifest.write_text(
            json.dumps(
                {
                    "schemaVersion": 1,
                    "kind": full_reference.REFERENCE_KIND,
                    "datasets": manifest_rows,
                }
            ),
            encoding="utf-8",
        )
        return manifest

    def test_candidate_index_returns_exact_same_scores_ranks_and_rows_as_full_index(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            full = full_reference.ReferenceIndex(manifest)
            light = candidate_reference.CandidateReferenceIndex(manifest)
            queries = (
                "Tomato",
                "tomatoes",
                "Brown sugar",
                "Sugar brown",
                "rice",
                "vegetables",
                "Solanum lycopersicum",
                "garden tomato",
                "fresh whole",
                "muscovado",
                "mirin",
                "passata",
                "kombu",
                "seitan",
                "gochujang",
                "does-not-exist",
            )
            for query in queries:
                with self.subTest(query=query):
                    self.assertEqual(
                        light._rank(query, max_candidates=20),
                        full._rank(query, max_candidates=20),
                    )
                    self.assertEqual(
                        light.search(query, max_candidates=8),
                        full.search(query, max_candidates=8),
                    )

            self.assertTrue(light.candidate_only)
            self.assertEqual(light.indexed_fdc_id_count, 10)
            self.assertEqual(len(light._score_rows), len(light.records))
            self.assertFalse(hasattr(light, "_raw_by_id"))
            self.assertFalse(
                any(key.startswith("_") for row in light.records for key in row),
                "private precomputed score metadata leaked into candidate rows",
            )

    def test_culinary_aliases_are_zero_result_fallback_and_remain_marked(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            full = full_reference.ReferenceIndex(manifest)
            light = candidate_reference.CandidateReferenceIndex(manifest)
            expected = {
                "mirin": (302, "rice wine"),
                "passata": (204, "tomato puree"),
                "kombu": (103, "kelp"),
                "seitan": (203, "wheat gluten"),
                "gochujang": (303, "red pepper paste"),
            }
            for query, (fdc_id, matched_query) in expected.items():
                with self.subTest(query=query):
                    self.assertEqual(light._rank(query, max_candidates=8), [])
                    rows = light.search(query, max_candidates=8)
                    self.assertTrue(rows)
                    self.assertEqual(rows[0]["fdcId"], fdc_id)
                    self.assertTrue(rows[0]["localEvidenceQueryAlias"])
                    self.assertEqual(rows[0]["localEvidenceMatchedQuery"], matched_query)
                    self.assertEqual(rows, full.search(query, max_candidates=8))

            # Even if a discovery alias exists for a name, literal evidence must
            # win and therefore must not be mislabeled as alias-derived.
            with patch.dict(
                full_reference._DISCOVERY_ALIASES,
                {"tomato": ("rice wine",)},
                clear=False,
            ):
                rows = light.search("Tomato", max_candidates=8)
            self.assertTrue(rows)
            self.assertEqual(rows[0]["fdcId"], 101)
            self.assertNotIn("localEvidenceQueryAlias", rows[0])
            self.assertNotIn("localEvidenceMatchedQuery", rows[0])

    def test_score_upper_bound_prunes_sequence_matching_without_changing_top_n(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = self._manifest(root)
            foundation = root / "foundation.json"
            payload = json.loads(foundation.read_text(encoding="utf-8"))
            payload["FoundationFoods"].extend(
                {
                    "fdcId": 1000 + index,
                    "description": f"Tomato product number {index} prepared with vegetables and sauce",
                }
                for index in range(1, 41)
            )
            foundation.write_text(json.dumps(payload), encoding="utf-8")

            full = full_reference.ReferenceIndex(manifest)
            light = candidate_reference.CandidateReferenceIndex(manifest)
            expected = full._rank("Tomato", max_candidates=1)
            original_matcher = candidate_reference.SequenceMatcher
            calls = 0

            def counted_matcher(*args, **kwargs):
                nonlocal calls
                calls += 1
                return original_matcher(*args, **kwargs)

            with patch.object(candidate_reference, "SequenceMatcher", side_effect=counted_matcher):
                actual = light._rank("Tomato", max_candidates=1)

            self.assertEqual(actual, expected)
            self.assertLess(calls, 10, "upper-bound pruning did not reduce ratio evaluations")
            self.assertGreater(len(light.records), 40)

    def test_candidate_index_cannot_be_used_for_exact_nutrition_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            light = candidate_reference.CandidateReferenceIndex(
                self._manifest(Path(directory))
            )
            with self.assertRaisesRegex(RuntimeError, "evidence-only"):
                light.food(101)
            with self.assertRaisesRegex(RuntimeError, "evidence-only"):
                light.metadata(101)


if __name__ == "__main__":
    unittest.main()
