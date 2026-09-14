from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import probe_release_catalog_v60_failed_details as probe  # noqa: E402


def catalog(*, failed_details: int = 1, unique: int = 2) -> dict:
    return {
        "schemaVersion": 1,
        "catalogVersion": "probe-test",
        "source": {
            "catalogs": [
                {
                    "language": "en",
                    "country": "GB",
                    "market": "GS_GB",
                    "uniqueVariants": unique,
                    "hydratedVariants": unique - failed_details,
                    "failedDetails": failed_details,
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
                    {
                        "variantId": "A",
                        "groupingFunctionalId": "G1",
                    }
                ],
            }
        ],
    }


def no_retry(func, *args, **kwargs):
    return func(*args, **kwargs)


class FailedDetailEvidenceV60Tests(unittest.TestCase):
    def test_only_failed_catalogs_are_searched_and_only_absent_ids_are_probed(self):
        seen_search: list[str] = []
        seen_detail: list[str] = []

        def search(_cfg, _tokens, _pcfg, **kwargs):
            seen_search.append(kwargs["language"])
            return [
                {"searchVariantId": "A"},
                {"searchVariantId": "B"},
            ]

        def detail(_cfg, _tokens, _pcfg, **kwargs):
            seen_detail.append(kwargs["variant_id"])
            raise probe.v59.catalog.CatalogError(
                "SEB recipe request failed: app=HTTP404"
            )

        result = probe.probe(
            catalog(),
            cfg={},
            tokens={"access_token": "DO-NOT-PERSIST"},
            pcfg={},
            configured_language="de",
            configured_country="DE",
            workers=1,
            search_func=search,
            detail_func=detail,
            search_retry=no_retry,
            detail_retry=no_retry,
        )

        self.assertEqual(seen_search, ["en"])
        self.assertEqual(seen_detail, ["B"])
        self.assertEqual(result["summary"]["declaredFailedDetailCount"], 1)
        self.assertEqual(result["summary"]["currentCandidateCount"], 1)
        self.assertEqual(result["summary"]["outcomes"], {"http-404": 1})
        row = result["catalogs"][0]
        self.assertTrue(row["searchManifestCountStable"])
        self.assertTrue(row["candidateCountMatchesDeclaredFailures"])
        self.assertFalse(row["historicalFailedIdsKnown"])
        self.assertEqual(row["evidence"][0]["variantId"], "B")

    def test_present_elsewhere_is_not_reprobed_or_claimed_as_known_failure(self):
        seen_detail: list[str] = []

        def search(_cfg, _tokens, _pcfg, **kwargs):
            return [
                {"searchVariantId": "A"},
                {"searchVariantId": "B"},
            ]

        def detail(_cfg, _tokens, _pcfg, **kwargs):
            seen_detail.append(kwargs["variant_id"])
            return {"variantId": kwargs["variant_id"]}

        result = probe.probe(
            catalog(failed_details=2, unique=2),
            cfg={},
            tokens={},
            pcfg={},
            configured_language="de",
            configured_country="DE",
            workers=1,
            search_func=search,
            detail_func=detail,
            search_retry=no_retry,
            detail_retry=no_retry,
        )

        self.assertEqual(seen_detail, ["B"])
        row = result["catalogs"][0]
        self.assertFalse(row["candidateCountMatchesDeclaredFailures"])
        self.assertEqual(row["unattributedDeclaredFailureCount"], 1)
        self.assertEqual(row["presentInCapturedCatalogCount"], 1)
        self.assertFalse(row["historicalFailedIdsKnown"])

    def test_manifest_count_drift_is_explicit_and_never_promoted_to_identity_proof(self):
        def search(_cfg, _tokens, _pcfg, **kwargs):
            return [
                {"searchVariantId": "A"},
                {"searchVariantId": "B"},
                {"searchVariantId": "C"},
            ]

        def detail(_cfg, _tokens, _pcfg, **kwargs):
            return {"variantId": kwargs["variant_id"]}

        result = probe.probe(
            catalog(),
            cfg={},
            tokens={},
            pcfg={},
            configured_language="de",
            configured_country="DE",
            workers=1,
            search_func=search,
            detail_func=detail,
            search_retry=no_retry,
            detail_retry=no_retry,
        )

        row = result["catalogs"][0]
        self.assertFalse(row["searchManifestCountStable"])
        self.assertFalse(row["candidateCountMatchesDeclaredFailures"])
        self.assertFalse(row["historicalFailedIdsKnown"])
        self.assertEqual(
            {item["variantId"] for item in row["evidence"]},
            {"B", "C"},
        )

    def test_exact_provider_variant_id_is_never_normalized_or_rewritten(self):
        exact_id = "PROVIDER:MiXeD_01/ABC"
        seen_detail: list[str] = []

        def search(_cfg, _tokens, _pcfg, **kwargs):
            return [
                {"searchVariantId": "A"},
                {"searchVariantId": exact_id},
            ]

        def detail(_cfg, _tokens, _pcfg, **kwargs):
            seen_detail.append(kwargs["variant_id"])
            return {"variantId": kwargs["variant_id"]}

        result = probe.probe(
            catalog(),
            cfg={},
            tokens={},
            pcfg={},
            configured_language="de",
            configured_country="DE",
            workers=1,
            search_func=search,
            detail_func=detail,
            search_retry=no_retry,
            detail_retry=no_retry,
        )

        self.assertEqual(seen_detail, [exact_id])
        self.assertEqual(
            result["catalogs"][0]["evidence"][0]["variantId"],
            exact_id,
        )
        self.assertFalse(result["policy"]["providerVariantIdentityInferred"])

    def test_failure_categories_are_bounded_and_do_not_persist_raw_messages(self):
        cases = [
            (
                probe.v59.catalog.CatalogAuthError(
                    "SEB recipe authentication failed (tokens redacted): "
                    "app=HTTP401 | id=HTTP403"
                ),
                {"outcome": "auth"},
            ),
            (
                probe.v59.catalog.CatalogError(
                    "SEB recipe request failed: app=HTTP404 | id=HTTP404"
                ),
                {"outcome": "http-404", "httpStatuses": [404]},
            ),
            (
                probe.v59.catalog.CatalogError(
                    "SEB recipe request failed: app=HTTP500 | id=HTTP503"
                ),
                {"outcome": "http-other", "httpStatuses": [500, 503]},
            ),
            (
                probe.v59.catalog.CatalogError(
                    "SEB recipe request failed: app=network:Timeout"
                ),
                {"outcome": "network-timeout-exhausted"},
            ),
            (
                probe.v59.catalog.CatalogError(
                    "SEB recipe request failed: app=network:ConnectError"
                ),
                {"outcome": "network-other"},
            ),
            (
                probe.v59.catalog.CatalogError(
                    "SEB recipe request failed: app=network:Timeout | id=HTTP404"
                ),
                {"outcome": "mixed-provider-failure", "httpStatuses": [404]},
            ),
            (
                probe.v59.catalog.CatalogError(
                    "SEB recipe endpoint returned invalid JSON: JSONDecodeError"
                ),
                {"outcome": "invalid-json"},
            ),
            (RuntimeError("SENSITIVE raw unexpected message"), {"outcome": "unexpected"}),
        ]

        for exc, expected in cases:
            with self.subTest(expected=expected):
                value = probe.classify_failure(exc)
                self.assertEqual(value, expected)
                rendered = json.dumps(value)
                self.assertNotIn("SENSITIVE", rendered)
                self.assertNotIn("app=", rendered)
                self.assertNotIn("id=", rendered)

    def test_search_failure_is_sanitized_and_does_not_abort_other_evidence(self):
        def search(_cfg, _tokens, _pcfg, **kwargs):
            raise probe.v59.catalog.CatalogAuthError(
                "SEB recipe authentication failed (tokens redacted): SECRET=HTTP401"
            )

        result = probe.probe(
            catalog(),
            cfg={},
            tokens={"password": "TOP-SECRET"},
            pcfg={},
            configured_language="de",
            configured_country="DE",
            workers=1,
            search_func=search,
            detail_func=lambda *_args, **_kwargs: {},
            search_retry=no_retry,
            detail_retry=no_retry,
        )

        self.assertEqual(result["summary"]["searchFailureCount"], 1)
        self.assertEqual(result["catalogs"][0]["searchFailure"], {"outcome": "auth"})
        rendered = json.dumps(result)
        self.assertNotIn("TOP-SECRET", rendered)
        self.assertNotIn("SECRET=HTTP401", rendered)
        self.assertFalse(result["secretsPersisted"])

    def test_probe_does_not_mutate_input_catalog(self):
        payload = catalog()
        before = deepcopy(payload)

        def search(_cfg, _tokens, _pcfg, **kwargs):
            return [{"searchVariantId": "A"}, {"searchVariantId": "B"}]

        def detail(_cfg, _tokens, _pcfg, **kwargs):
            return {"variantId": kwargs["variant_id"]}

        probe.probe(
            payload,
            cfg={},
            tokens={},
            pcfg={},
            configured_language="de",
            configured_country="DE",
            workers=1,
            search_func=search,
            detail_func=detail,
            search_retry=no_retry,
            detail_retry=no_retry,
        )
        self.assertEqual(payload, before)

    def test_detail_retry_contract_is_injected_without_changing_call_arguments(self):
        seen: list[tuple[object, ...]] = []

        def search(_cfg, _tokens, _pcfg, **kwargs):
            return [{"searchVariantId": "A"}, {"searchVariantId": "B"}]

        def detail(_cfg, _tokens, _pcfg, **kwargs):
            seen.append(
                (
                    kwargs["variant_id"],
                    kwargs["source_language"],
                    kwargs["configured_language"],
                    kwargs["configured_country"],
                )
            )
            return {"variantId": kwargs["variant_id"]}

        def detail_retry(func, *args, **kwargs):
            return func(*args, **kwargs)

        probe.probe(
            catalog(),
            cfg={},
            tokens={},
            pcfg={},
            configured_language="de",
            configured_country="DE",
            workers=1,
            search_func=search,
            detail_func=detail,
            search_retry=no_retry,
            detail_retry=detail_retry,
        )

        self.assertEqual(seen, [("B", "en", "de", "DE")])


if __name__ == "__main__":
    unittest.main()
