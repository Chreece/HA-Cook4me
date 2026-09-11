from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog_v60_reviewed as reviewed  # noqa: E402
import release_catalog_detail_not_found_v60 as detail_not_found  # noqa: E402


class FakeCatalogError(RuntimeError):
    pass


class FakeCatalogAuthError(FakeCatalogError):
    pass


FAKE_CATALOG = types.SimpleNamespace(
    CatalogError=FakeCatalogError,
    CatalogAuthError=FakeCatalogAuthError,
)


PROVEN_404 = FakeCatalogAuthError(
    "SEB recipe authentication failed (tokens redacted): "
    "app=HTTP404 | access_rcu=HTTP404 | access_rcu_remote=HTTP401 | "
    "id_rcu=HTTP401 | id_rcu_remote=HTTP401 | access_bearer=HTTP401 | "
    "id_bearer=HTTP401"
)


def base_payload() -> dict:
    return {
        "schemaVersion": 1,
        "catalogVersion": "detail-not-found-test",
        "complete": False,
        "source": {
            "auditedCatalogCount": 1,
            "catalogs": [
                {
                    "language": "en",
                    "country": "GB",
                    "market": "GS_GB",
                    "uniqueVariants": 2,
                    "hydratedVariants": 2,
                    "failedDetails": 0,
                }
            ],
            "failedDetailCount": 0,
            "unresolvedCanonicalIngredientNames": 0,
            "unresolvedCanonicalRecipeNames": 1,
            "nutritionRequiredForComplete": False,
        },
        "ingredients": [],
        "recipes": [
            {
                "groupingFunctionalId": "G-A",
                "canonicalName": "A",
                "variants": [
                    {
                        "variantId": "A",
                        "groupingFunctionalId": "G-A",
                        "title": "A",
                        "language": "en",
                    }
                ],
            },
            {
                "canonicalEnglishNeedsReview": True,
                "variants": [{"variantId": "B", "language": "en"}],
            },
        ],
    }


class DetailNotFoundClassificationTests(unittest.TestCase):
    def test_exact_live_proven_app_and_access_rcu_404_shape_is_accepted(self):
        self.assertTrue(
            detail_not_found.is_search_listed_detail_not_found(
                PROVEN_404,
                FAKE_CATALOG,
            )
        )

    def test_app_404_without_access_rcu_404_is_not_accepted(self):
        exc = FakeCatalogAuthError(
            "SEB recipe authentication failed (tokens redacted): "
            "app=HTTP404 | access_rcu=HTTP401 | id_rcu=HTTP401"
        )
        self.assertFalse(
            detail_not_found.is_search_listed_detail_not_found(exc, FAKE_CATALOG)
        )

    def test_network_or_non_auth_failures_are_not_accepted(self):
        for exc in (
            FakeCatalogAuthError(
                "SEB recipe authentication failed (tokens redacted): "
                "app=HTTP404 | access_rcu=HTTP404 | id_rcu=network:Timeout"
            ),
            FakeCatalogError(
                "SEB recipe request failed: app=HTTP404 | access_rcu=HTTP404"
            ),
            RuntimeError("app=HTTP404 | access_rcu=HTTP404"),
        ):
            with self.subTest(exc=type(exc).__name__):
                self.assertFalse(
                    detail_not_found.is_search_listed_detail_not_found(
                        exc,
                        FAKE_CATALOG,
                    )
                )

    def test_unknown_provider_mode_fails_closed(self):
        exc = FakeCatalogAuthError(
            "SEB recipe authentication failed (tokens redacted): "
            "app=HTTP404 | access_rcu=HTTP404 | SECRET_MODE=HTTP401"
        )
        self.assertEqual(detail_not_found.safe_provider_results(exc), {})
        self.assertFalse(
            detail_not_found.is_search_listed_detail_not_found(exc, FAKE_CATALOG)
        )


class DetailNotFoundCaptureTests(unittest.TestCase):
    def test_exact_404_is_accounted_and_omitted_without_relaxing_other_failures(self):
        def raw_detail(_cfg=None, _tokens=None, _pcfg=None, **kwargs):
            if kwargs["variant_id"] == "B":
                raise PROVEN_404
            return {
                "variantId": kwargs["variant_id"],
                "recipeFunctionalId": kwargs["variant_id"],
                "groupingFunctionalId": "G-A",
                "title": "A",
                "language": "en",
                "ingredients": [],
            }

        fake_v59 = types.SimpleNamespace(
            _detail=raw_detail,
            catalog=FAKE_CATALOG,
        )
        original_detail = fake_v59._detail

        def build_func(v59, _args):
            rows = []
            for variant_id in ("A", "B"):
                rows.append(
                    v59._detail(
                        None,
                        None,
                        None,
                        variant_id=variant_id,
                        source_language="en",
                        configured_language="de",
                        configured_country="DE",
                    )
                )
            payload = base_payload()
            payload["recipes"] = [
                {
                    "groupingFunctionalId": "G-A",
                    "canonicalName": "A",
                    "variants": [deepcopy(rows[0])],
                },
                {
                    "canonicalEnglishNeedsReview": True,
                    "variants": [deepcopy(rows[1])],
                },
            ]
            return payload

        result = detail_not_found.build_with_detail_not_found(
            fake_v59,
            build_func,
            object(),
        )

        self.assertIs(fake_v59._detail, original_detail)
        self.assertEqual(result["source"]["failedDetailCount"], 0)
        self.assertEqual(result["source"]["detailNotFoundCount"], 1)
        row = result["source"]["catalogs"][0]
        self.assertEqual(row["hydratedVariants"], 1)
        self.assertEqual(row["detailNotFoundCount"], 1)
        self.assertEqual(row["detailNotFoundVariantIds"], ["B"])
        self.assertEqual(
            [
                variant["variantId"]
                for group in result["recipes"]
                for variant in group.get("variants") or []
            ],
            ["A"],
        )
        self.assertEqual(result["source"]["unresolvedCanonicalRecipeNames"], 0)
        self.assertEqual(detail_not_found.validation_errors(result), [])

    def test_non_matching_failure_still_raises_and_hook_is_restored(self):
        failure = FakeCatalogAuthError(
            "SEB recipe authentication failed (tokens redacted): "
            "app=HTTP401 | access_rcu=HTTP401"
        )

        def raw_detail(*_args, **_kwargs):
            raise failure

        fake_v59 = types.SimpleNamespace(_detail=raw_detail, catalog=FAKE_CATALOG)
        original_detail = fake_v59._detail

        def build_func(v59, _args):
            v59._detail(
                variant_id="B",
                source_language="en",
            )
            raise AssertionError("unreachable")

        with self.assertRaises(FakeCatalogAuthError):
            detail_not_found.build_with_detail_not_found(
                fake_v59,
                build_func,
                object(),
            )
        self.assertIs(fake_v59._detail, original_detail)


class DetailNotFoundValidationTests(unittest.TestCase):
    def valid_accounted_payload(self) -> dict:
        payload = base_payload()
        payload["recipes"] = [payload["recipes"][0]]
        payload["source"]["catalogs"][0].update(
            {
                "hydratedVariants": 1,
                "failedDetails": 0,
                "detailNotFoundCount": 1,
                "detailNotFoundVariantIds": ["B"],
            }
        )
        payload["source"].update(
            {
                "detailNotFoundCount": 1,
                "detailNotFoundPolicy": detail_not_found._POLICY,
                "detailNotFoundVariantIdsStored": True,
                "unresolvedCanonicalRecipeNames": 0,
            }
        )
        return payload

    def test_exact_accounting_is_complete_for_capture_gate(self):
        payload = self.valid_accounted_payload()
        self.assertEqual(detail_not_found.validation_errors(payload), [])
        self.assertTrue(reviewed._capture_complete(payload))

    def test_count_or_identity_drift_fails_closed(self):
        payload = self.valid_accounted_payload()
        payload["source"]["catalogs"][0]["hydratedVariants"] = 2
        errors = detail_not_found.validation_errors(payload)
        self.assertTrue(
            any("detail accounting does not equal uniqueVariants" in item for item in errors)
        )
        self.assertFalse(reviewed._capture_complete(payload))

        payload = self.valid_accounted_payload()
        payload["source"]["catalogs"][0]["detailNotFoundVariantIds"] = ["C"]
        # A different exact provider ID is still structurally valid; identity
        # semantics are established during live capture, not inferred offline.
        self.assertEqual(detail_not_found.validation_errors(payload), [])

        payload["source"]["detailNotFoundPolicy"] = "relaxed"
        self.assertTrue(detail_not_found.validation_errors(payload))
        self.assertFalse(reviewed._capture_complete(payload))

    def test_failed_details_remain_incomplete_even_when_arithmetic_reconciles(self):
        payload = self.valid_accounted_payload()
        row = payload["source"]["catalogs"][0]
        row["hydratedVariants"] = 0
        row["failedDetails"] = 1
        payload["source"]["failedDetailCount"] = 1
        self.assertEqual(detail_not_found.validation_errors(payload), [])
        self.assertFalse(reviewed._capture_complete(payload))


if __name__ == "__main__":
    unittest.main()
