from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COMPONENT = ROOT / "custom_components" / "cook4me"
for path in (TOOLS, COMPONENT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import build_release_catalog_v60_reviewed as reviewed  # noqa: E402


class ReleaseCatalogV60DetailTimeoutRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = reviewed.base._core.v59.catalog

    def test_pure_timeout_retries_identical_detail_request_then_succeeds(self) -> None:
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        sleeps: list[float] = []

        def detail(*args, **kwargs):
            calls.append((args, dict(kwargs)))
            if len(calls) == 1:
                raise self.catalog.CatalogError(
                    "SEB recipe request failed: app=network:Timeout"
                )
            return {"variantId": "recipe-1"}

        result = reviewed._retry_detail(
            detail,
            "cfg",
            "tokens",
            variant_id="recipe-1",
            source_language="de",
            configured_language="de",
            configured_country="DE",
            sleep_func=sleeps.append,
        )

        self.assertEqual(result, {"variantId": "recipe-1"})
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(sleeps, [reviewed._DETAIL_TIMEOUT_DELAY_SECONDS])

    def test_pure_timeout_stops_after_three_total_detail_attempts(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def detail(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise self.catalog.CatalogError(
                "SEB recipe request failed: app=network:Timeout"
            )

        with self.assertRaises(self.catalog.CatalogError):
            reviewed._retry_detail(
                detail,
                variant_id="recipe-1",
                sleep_func=sleeps.append,
            )

        self.assertEqual(calls, reviewed._DETAIL_TIMEOUT_ATTEMPTS)
        self.assertEqual(
            sleeps,
            [reviewed._DETAIL_TIMEOUT_DELAY_SECONDS]
            * (reviewed._DETAIL_TIMEOUT_ATTEMPTS - 1),
        )

    def test_auth_http_mixed_and_unrelated_detail_failures_never_retry(self) -> None:
        cases = (
            self.catalog.CatalogAuthError(
                "SEB recipe authentication failed (tokens redacted): app=HTTP401"
            ),
            self.catalog.CatalogError("SEB recipe request failed: app=HTTP500"),
            self.catalog.CatalogError(
                "SEB recipe request failed: app=network:Timeout | access_rcu=HTTP500"
            ),
            RuntimeError("not a provider timeout"),
        )
        for failure in cases:
            with self.subTest(failure=type(failure).__name__, message=str(failure)):
                calls = 0

                def detail(*args, **kwargs):
                    nonlocal calls
                    calls += 1
                    raise failure

                with self.assertRaises(type(failure)):
                    reviewed._retry_detail(
                        detail,
                        variant_id="recipe-1",
                        sleep_func=lambda _seconds: self.fail("must not sleep"),
                    )
                self.assertEqual(calls, 1)

    def test_build_wrapper_installs_both_retry_stages_and_restores_after_success(self) -> None:
        v59 = reviewed.base._core.v59
        actual_search = v59._all_search_rows
        actual_detail = v59._detail
        actual_build = reviewed.base.build

        def original_search(*args, **kwargs):
            return [{"searchVariantId": "recipe-1"}]

        def original_detail(*args, **kwargs):
            return {"variantId": kwargs.get("variant_id")}

        seen: dict[str, object] = {}

        def fake_build(args):
            seen["search"] = v59._all_search_rows
            seen["detail"] = v59._detail
            self.assertIsNot(v59._all_search_rows, original_search)
            self.assertIsNot(v59._detail, original_detail)
            self.assertEqual(
                v59._all_search_rows(language="de", country="DE"),
                [{"searchVariantId": "recipe-1"}],
            )
            self.assertEqual(
                v59._detail(variant_id="recipe-1"),
                {"variantId": "recipe-1"},
            )
            return {"complete": True}

        v59._all_search_rows = original_search
        v59._detail = original_detail
        reviewed.base.build = fake_build
        try:
            self.assertEqual(
                reviewed._build_with_search_timeout_retry(object()),
                {"complete": True},
            )
            self.assertIs(v59._all_search_rows, original_search)
            self.assertIs(v59._detail, original_detail)
            self.assertIn("search", seen)
            self.assertIn("detail", seen)
        finally:
            reviewed.base.build = actual_build
            v59._all_search_rows = actual_search
            v59._detail = actual_detail

    def test_build_wrapper_restores_both_retry_stages_after_failure(self) -> None:
        v59 = reviewed.base._core.v59
        actual_search = v59._all_search_rows
        actual_detail = v59._detail
        actual_build = reviewed.base.build

        def original_search(*args, **kwargs):
            return []

        def original_detail(*args, **kwargs):
            return {}

        def fake_build(args):
            self.assertIsNot(v59._all_search_rows, original_search)
            self.assertIsNot(v59._detail, original_detail)
            raise RuntimeError("synthetic build failure")

        v59._all_search_rows = original_search
        v59._detail = original_detail
        reviewed.base.build = fake_build
        try:
            with self.assertRaisesRegex(RuntimeError, "synthetic build failure"):
                reviewed._build_with_search_timeout_retry(object())
            self.assertIs(v59._all_search_rows, original_search)
            self.assertIs(v59._detail, original_detail)
        finally:
            reviewed.base.build = actual_build
            v59._all_search_rows = actual_search
            v59._detail = actual_detail


if __name__ == "__main__":
    unittest.main()
