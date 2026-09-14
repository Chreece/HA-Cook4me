from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

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
                    }
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
            self.assertEqual(light.indexed_fdc_id_count, 5)
            self.assertEqual(len(light._score_rows), len(light.records))
            self.assertFalse(hasattr(light, "_raw_by_id"))
            self.assertFalse(
                any(key.startswith("_") for row in light.records for key in row),
                "private precomputed score metadata leaked into candidate rows",
            )

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
