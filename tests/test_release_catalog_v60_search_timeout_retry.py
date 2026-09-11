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


class ReleaseCatalogV60SearchTimeoutRetryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = reviewed.base._core.v59.catalog

    def test_pure_timeout_retries_identical_request_then_succeeds(self) -> None:
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        sleeps: list[float] = []

        def search(*args, **kwargs):
            calls.append((args, dict(kwargs)))
            if len(calls) == 1:
                raise self.catalog.CatalogError(
                    "SEB recipe request failed: app=network:Timeout"
                )
            return [{"searchVariantId": "recipe-1"}]

        result = reviewed._retry_search_rows(
            search,
            "cfg",
            "tokens",
            language="bg",
            country="BG",
            configured_language="de",
            configured_country="DE",
            sleep_func=sleeps.append,
        )

        self.assertEqual(result, [{"searchVariantId": "recipe-1"}])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(sleeps, [reviewed._SEARCH_TIMEOUT_DELAY_SECONDS])

    def test_pure_timeout_stops_after_three_total_attempts(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def search(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise self.catalog.CatalogError(
                "SEB recipe request failed: app=network:Timeout"
            )

        with self.assertRaises(self.catalog.CatalogError):
            reviewed._retry_search_rows(
                search,
                language="bg",
                country="BG",
                sleep_func=sleeps.append,
            )

        self.assertEqual(calls, reviewed._SEARCH_TIMEOUT_ATTEMPTS)
        self.assertEqual(
            sleeps,
            [reviewed._SEARCH_TIMEOUT_DELAY_SECONDS]
            * (reviewed._SEARCH_TIMEOUT_ATTEMPTS - 1),
        )

    def test_auth_failure_never_retries(self) -> None:
        calls = 0
        sleeps: list[float] = []

        def search(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise self.catalog.CatalogAuthError(
                "SEB recipe authentication failed (tokens redacted): "
                "app=network:Timeout | access_rcu=HTTP401"
            )

        with self.assertRaises(self.catalog.CatalogAuthError):
            reviewed._retry_search_rows(
                search,
                language="bg",
                country="BG",
                sleep_func=sleeps.append,
            )

        self.assertEqual(calls, 1)
        self.assertEqual(sleeps, [])

    def test_http_failure_never_retries(self) -> None:
        calls = 0

        def search(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise self.catalog.CatalogError(
                "SEB recipe request failed: app=HTTP500"
            )

        with self.assertRaises(self.catalog.CatalogError):
            reviewed._retry_search_rows(
                search,
                language="bg",
                country="BG",
                sleep_func=lambda _seconds: self.fail("must not sleep"),
            )
        self.assertEqual(calls, 1)

    def test_mixed_timeout_and_http_failure_never_retries(self) -> None:
        calls = 0

        def search(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise self.catalog.CatalogError(
                "SEB recipe request failed: "
                "app=network:Timeout | access_rcu=HTTP500"
            )

        with self.assertRaises(self.catalog.CatalogError):
            reviewed._retry_search_rows(
                search,
                language="bg",
                country="BG",
                sleep_func=lambda _seconds: self.fail("must not sleep"),
            )
        self.assertEqual(calls, 1)

    def test_unrelated_exception_never_retries(self) -> None:
        calls = 0

        def search(*args, **kwargs):
            nonlocal calls
            calls += 1
            raise RuntimeError("not a provider network timeout")

        with self.assertRaises(RuntimeError):
            reviewed._retry_search_rows(
                search,
                language="bg",
                country="BG",
                sleep_func=lambda _seconds: self.fail("must not sleep"),
            )
        self.assertEqual(calls, 1)

    def test_build_wrapper_restores_original_search_after_success(self) -> None:
        v59 = reviewed.base._core.v59
        actual_search = v59._all_search_rows
        actual_build = reviewed.base.build

        def original_search(*args, **kwargs):
            return [{"searchVariantId": "recipe-1"}]

        seen_wrapper = None

        def fake_build(args):
            nonlocal seen_wrapper
            seen_wrapper = v59._all_search_rows
            self.assertIsNot(seen_wrapper, original_search)
            self.assertEqual(
                seen_wrapper(language="bg", country="BG"),
                [{"searchVariantId": "recipe-1"}],
            )
            return {"complete": True}

        v59._all_search_rows = original_search
        reviewed.base.build = fake_build
        try:
            result = reviewed._build_with_search_timeout_retry(object())
            self.assertEqual(result, {"complete": True})
            self.assertIs(v59._all_search_rows, original_search)
            self.assertIsNotNone(seen_wrapper)
        finally:
            reviewed.base.build = actual_build
            v59._all_search_rows = actual_search

    def test_build_wrapper_restores_original_search_after_failure(self) -> None:
        v59 = reviewed.base._core.v59
        actual_search = v59._all_search_rows
        actual_build = reviewed.base.build

        def original_search(*args, **kwargs):
            return []

        def fake_build(args):
            self.assertIsNot(v59._all_search_rows, original_search)
            raise RuntimeError("synthetic build failure")

        v59._all_search_rows = original_search
        reviewed.base.build = fake_build
        try:
            with self.assertRaisesRegex(RuntimeError, "synthetic build failure"):
                reviewed._build_with_search_timeout_retry(object())
            self.assertIs(v59._all_search_rows, original_search)
        finally:
            reviewed.base.build = actual_build
            v59._all_search_rows = actual_search


if __name__ == "__main__":
    unittest.main()
