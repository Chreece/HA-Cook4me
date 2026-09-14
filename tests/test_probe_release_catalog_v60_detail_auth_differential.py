from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import probe_release_catalog_v60_detail_auth_differential as probe  # noqa: E402


def no_retry(func, *args, **kwargs):
    return func(*args, **kwargs)


def catalog() -> dict:
    return {
        "schemaVersion": 1,
        "catalogVersion": "capture-test",
        "source": {
            "catalogs": [
                {
                    "language": "en",
                    "country": "GB",
                    "market": "GS_GB",
                    "uniqueVariants": 6,
                    "hydratedVariants": 3,
                    "failedDetails": 3,
                },
                {
                    "language": "de",
                    "country": "DE",
                    "market": "GS_DE",
                    "uniqueVariants": 1,
                    "hydratedVariants": 1,
                    "failedDetails": 0,
                },
            ]
        },
        "recipes": [
            {
                "groupingFunctionalId": "G1",
                "variants": [
                    {"variantId": "A"},
                    {"variantId": "C"},
                    {"variantId": "E"},
                ],
            }
        ],
    }


class DetailAuthDifferentialV60Tests(unittest.TestCase):
    def test_catalog_auth_404_is_not_collapsed_into_generic_auth(self):
        exc = probe.v59.catalog.CatalogAuthError(
            "SEB recipe authentication failed (tokens redacted): "
            "app=HTTP404 | access_rcu=HTTP401 | access_rcu_remote=HTTP401 | "
            "id_rcu=HTTP403 | id_bearer=HTTP401"
        )
        result = probe.classify_detail_failure(exc)
        self.assertEqual(result["outcome"], "app-404-auth-fallbacks")
        self.assertEqual(result["httpStatuses"], [401, 403, 404])
        self.assertEqual(result["providerResults"]["app"], "HTTP404")
        rendered = json.dumps(result)
        self.assertNotIn("tokens redacted", rendered)
        self.assertNotIn("SEB recipe", rendered)

    def test_pure_401_403_remains_auth(self):
        exc = probe.v59.catalog.CatalogAuthError(
            "SEB recipe authentication failed (tokens redacted): "
            "app=HTTP401 | access_rcu=HTTP403 | id_bearer=HTTP401"
        )
        result = probe.classify_detail_failure(exc)
        self.assertEqual(result["outcome"], "auth")
        self.assertEqual(result["httpStatuses"], [401, 403])

    def test_unknown_provider_mode_is_not_persisted(self):
        exc = probe.v59.catalog.CatalogAuthError(
            "SEB recipe authentication failed (tokens redacted): "
            "SECRET_MODE=HTTP418 | app=HTTP401"
        )
        result = probe.classify_detail_failure(exc)
        self.assertEqual(result["providerResults"], {"app": "HTTP401"})
        self.assertNotIn("SECRET_MODE", json.dumps(result))

    def test_deterministic_spread_sampling_keeps_edges(self):
        self.assertEqual(probe._sample_ids(["1", "2", "3", "4", "5"], 3), ["1", "3", "5"])
        self.assertEqual(probe._sample_ids(["B", "A", "C"], 1), ["A"])
        self.assertEqual(probe._sample_ids(["B", "A", "C"], 9), ["A", "B", "C"])

    def test_probe_samples_only_failed_catalog_and_compares_controls(self):
        seen_search: list[str] = []
        seen_detail: list[str] = []

        def search(_cfg, _tokens, _pcfg, **kwargs):
            seen_search.append(kwargs["language"])
            return [
                {"searchVariantId": "A", "groupingFunctionalId": "GA"},
                {"searchVariantId": "B", "groupingFunctionalId": "GB"},
                {"searchVariantId": "C", "groupingFunctionalId": "GC"},
                {"searchVariantId": "D", "groupingFunctionalId": "GD"},
                {"searchVariantId": "E", "groupingFunctionalId": "GE"},
                {"searchVariantId": "F", "groupingFunctionalId": "GF"},
            ]

        def detail(_cfg, _tokens, _pcfg, **kwargs):
            variant = kwargs["variant_id"]
            seen_detail.append(variant)
            if variant in {"B", "D", "F"}:
                raise probe.v59.catalog.CatalogAuthError(
                    "SEB recipe authentication failed (tokens redacted): "
                    "app=HTTP404 | access_rcu=HTTP401 | id_bearer=HTTP401"
                )
            return {"variantId": variant}

        result = probe.probe(
            catalog(),
            cfg={},
            tokens={"access_token": "DO-NOT-PERSIST"},
            pcfg={},
            configured_language="de",
            configured_country="DE",
            candidate_samples=3,
            control_samples=1,
            search_func=search,
            detail_func=detail,
            search_retry=no_retry,
            detail_retry=no_retry,
        )

        self.assertEqual(seen_search, ["en"])
        self.assertEqual(set(seen_detail), {"A", "B", "D", "F"})
        self.assertEqual(result["summary"]["sampleCount"], 4)
        self.assertEqual(
            result["summary"]["outcomes"],
            {"app-404-auth-fallbacks": 3, "success-now": 1},
        )
        row = result["catalogs"][0]
        self.assertEqual(row["candidateSamples"], ["B", "D", "F"])
        self.assertEqual(row["controlSamples"], ["A"])
        candidate = next(item for item in row["samples"] if item["variantId"] == "B")
        self.assertEqual(candidate["searchIdentity"]["groupingFunctionalId"], "GB")
        rendered = json.dumps(result)
        self.assertNotIn("DO-NOT-PERSIST", rendered)
        self.assertFalse(result["secretsPersisted"])

    def test_sample_limits_are_hard_bounded(self):
        with self.assertRaises(ValueError):
            probe.probe(
                catalog(),
                cfg={},
                tokens={},
                pcfg={},
                configured_language="de",
                configured_country="DE",
                candidate_samples=10,
                control_samples=1,
            )
        with self.assertRaises(ValueError):
            probe.probe(
                catalog(),
                cfg={},
                tokens={},
                pcfg={},
                configured_language="de",
                configured_country="DE",
                candidate_samples=1,
                control_samples=4,
            )

    def test_token_permission_error_is_explicit_not_empty_store(self):
        with mock.patch.object(Path, "read_text", side_effect=PermissionError()):
            with self.assertRaisesRegex(RuntimeError, "not readable by current user"):
                probe._load_tokens(Path("/private/storage"))

    def test_empty_token_object_is_reported_exactly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / ".config" / "cook4me"
            path.mkdir(parents=True)
            (path / "tokens.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "empty JSON object"):
                probe._load_tokens(Path(temp_dir))


if __name__ == "__main__":
    unittest.main()
