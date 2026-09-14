from __future__ import annotations

import importlib.util
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
                    {"fdcId": 202, "description": "Sugar, brown"},
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
            (root / filename).write_text(
                json.dumps({key: rows}), encoding="utf-8"
            )
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

    def test_candidate_index_returns_same_candidate_search_as_full_index(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = self._manifest(Path(directory))
            full = full_reference.ReferenceIndex(manifest)
            light = candidate_reference.CandidateReferenceIndex(manifest)
            for query in ("Tomato", "Brown sugar", "rice", "vegetables"):
                with self.subTest(query=query):
                    self.assertEqual(
                        light.search(query, max_candidates=8),
                        full.search(query, max_candidates=8),
                    )
            self.assertTrue(light.candidate_only)
            self.assertEqual(light.indexed_fdc_id_count, 5)
            self.assertFalse(hasattr(light, "_raw_by_id"))

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
