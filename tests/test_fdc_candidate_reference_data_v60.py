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


class _DiscoveryFallbackIndex(full_reference.ReferenceIndex):
    """Tiny deterministic search double for fallback-order regressions."""

    def __init__(self, ranked_by_query):
        self.ranked_by_query = ranked_by_query
        self.calls = []

    def _rank(self, query: str, *, max_candidates: int):
        self.calls.append(query)
        return list(self.ranked_by_query.get(query, ()))[:max_candidates]


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
                    {"fdcId": 303, "description": "Bread, Italian"},
                    {"fdcId": 304, "description": "Wine, sparkling"},
                    {"fdcId": 305, "description": "Seaweed, dried"},
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
                "2 tbsp mirin",
                "passata",
                "kombu",
                "Kombu (3x3)",
                "seitan",
                "ciabatta",
                "prosecco",
                "Nori sheets",
                "Nori sheet (optional)",
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
            self.assertEqual(light.indexed_fdc_id_count, 12)
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
                "2 tbsp mirin": (302, "rice wine"),
                "passata": (204, "tomato puree"),
                "kombu": (103, "kelp"),
                "Kombu (3x3)": (103, "kelp"),
                "seitan": (203, "wheat gluten"),
                "ciabatta": (303, "italian bread"),
                "prosecco": (304, "sparkling wine"),
                "Nori sheets": (305, "dried seaweed"),
                "Nori sheet (optional)": (305, "dried seaweed"),
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

    def test_section_prefix_is_zero_result_marked_discovery_fallback(self):
        literal = (
            90.0,
            900,
            {"fdcId": 900, "description": "Literal result", "dataType": "SR Legacy"},
        )
        stripped = (
            80.0,
            800,
            {"fdcId": 800, "description": "Udon", "dataType": "Survey (FNDDS)"},
        )

        # Literal evidence stays first and is never mislabeled as transformed.
        index = _DiscoveryFallbackIndex({"B- udon": [literal], "udon": [stripped]})
        rows = index.search("B- udon")
        self.assertEqual(index.calls, ["B- udon"])
        self.assertEqual(rows[0]["fdcId"], 900)
        self.assertNotIn("localEvidenceQueryAlias", rows[0])
        self.assertNotIn("localEvidenceMatchedQuery", rows[0])

        # Only a literal miss permits stripping the uppercase section prefix.
        index = _DiscoveryFallbackIndex({"udon": [stripped]})
        rows = index.search("B- udon")
        self.assertEqual(index.calls, ["B- udon", "udon"])
        self.assertEqual(rows[0]["fdcId"], 800)
        self.assertTrue(rows[0]["localEvidenceQueryAlias"])
        self.assertEqual(rows[0]["localEvidenceMatchedQuery"], "udon")

    def test_section_prefix_can_chain_to_existing_static_alias(self):
        crumbs = (
            70.0,
            700,
            {"fdcId": 700, "description": "Bread crumbs", "dataType": "SR Legacy"},
        )
        index = _DiscoveryFallbackIndex({"bread crumbs": [crumbs]})
        rows = index.search("B- breadcrumbs")
        self.assertEqual(index.calls, ["B- breadcrumbs", "breadcrumbs", "bread crumbs"])
        self.assertEqual(rows[0]["fdcId"], 700)
        self.assertTrue(rows[0]["localEvidenceQueryAlias"])
        self.assertEqual(rows[0]["localEvidenceMatchedQuery"], "bread crumbs")

    def test_section_prefix_syntax_does_not_strip_food_names_or_lowercase(self):
        self.assertEqual(full_reference._section_prefix_query("A- udon"), "udon")
        self.assertEqual(full_reference._section_prefix_query("B-   breadcrumbs"), "breadcrumbs")
        self.assertEqual(full_reference._section_prefix_query("D-ribose"), "")
        self.assertEqual(full_reference._section_prefix_query("b- udon"), "")
        self.assertEqual(full_reference._section_prefix_query("A-"), "")

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
