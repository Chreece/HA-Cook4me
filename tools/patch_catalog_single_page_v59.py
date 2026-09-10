#!/usr/bin/env python3
"""Temporary maintenance patch for the proven single-page release crawl contract."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source_path = ROOT / "tools" / "crawl_release_catalog_v2.py"
text = source_path.read_text(encoding="utf-8")
text = text.replace("PAGE_SIZE = 50\n", "PAGE_SIZE = 5000\n", 1)
start = text.index("def _search_catalog(\n")
end = text.index("\ndef _status_codes", start)
replacement = '''def _search_catalog(
    cfg: dict[str, Any],
    tokens: dict[str, Any],
    pcfg: dict[str, Any],
    *,
    language: str,
    country: str,
    configured_language: str,
    configured_country: str,
) -> list[dict[str, Any]]:
    """Capture one complete provider catalog in the proven stable single page.

    A 2026-09-10 read-only all-28 probe proved size=5000 returns every current
    row in one response with stable repeated ID sets. Smaller paged requests
    showed page drift. Fail closed if the provider ever outgrows or violates
    this contract instead of silently assembling an incomplete release catalog.
    """
    market = f"GS_{country}"
    url = cfg["platform_base_url"].rstrip("/") + "/common-api/v4/search/recipes"
    payload, _auth = catalog._http_json(
        "POST",
        url,
        headers_iter=_headers(cfg, tokens, configured_country, configured_language, url, pcfg),
        params={
            "lang": language,
            "market": market,
            "page": 0,
            "size": PAGE_SIZE,
            "q": "",
            "groupBy": "",
            "myUniverse": "false",
            "myOwnRecipe": "false",
            "withAutomaticSpellcheck": "true",
        },
        body=_search_body(language, market),
        timeout=30,
    )
    if not isinstance(payload, dict):
        raise RuntimeError(f"{language}/{market}: invalid search response")
    page_info = payload.get("page")
    if not isinstance(page_info, dict):
        raise RuntimeError(f"{language}/{market}: search response is missing page metadata")
    try:
        total_elements = int(page_info["totalElements"])
        total_pages = int(page_info["totalPages"])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError(f"{language}/{market}: invalid search page metadata") from None
    if total_pages not in {0, 1}:
        raise RuntimeError(
            f"{language}/{market}: provider catalog exceeds proven single-page "
            f"capture size={PAGE_SIZE} (totalPages={total_pages}, totalElements={total_elements})"
        )

    content = payload.get("content") if isinstance(payload.get("content"), list) else []
    if len(content) != total_elements:
        raise RuntimeError(
            f"{language}/{market}: single-page response row count does not match provider total "
            f"(content={len(content)}, totalElements={total_elements})"
        )

    rows: list[dict[str, Any]] = []
    for raw in content:
        if not isinstance(raw, dict):
            raise RuntimeError(f"{language}/{market}: non-object recipe search row")
        ident = raw.get("identifier") if isinstance(raw.get("identifier"), dict) else {}
        variant = _fid(ident) or _fid(raw.get("fid")) or _fid(raw.get("functionalId"))
        if not variant:
            raise RuntimeError(f"{language}/{market}: recipe search row is missing provider identity")
        cover_url = _text(catalog._search_cover(raw))
        rows.append(
            {
                "variantId": variant,
                "sourceSystem": _text(ident.get("sourceSystem")),
                "version": _text(ident.get("version")),
                "groupingFunctionalId": _fid(raw.get("groupingId")),
                "title": _text(raw.get("title") or raw.get("shortTitle") or raw.get("normalizedTitle")),
                "language": _text(raw.get("lang")).lower() or language.lower(),
                "market": _text(raw.get("market")).upper() or market,
                "cover": cover_url,
                "servings": (catalog._yield(raw) or {}).get("quantity") or raw.get("groupSize"),
            }
        )
    ids = [row["variantId"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError(
            f"{language}/{market}: duplicate provider functional IDs in proven single-page response"
        )
    return rows
'''
text = text[:start] + replacement + text[end:]
source_path.write_text(text, encoding="utf-8")

test_path = ROOT / "tests" / "test_release_catalog_v2_crawler.py"
tests = test_path.read_text(encoding="utf-8")
if "from unittest.mock import patch\n" not in tests:
    tests = tests.replace("import unittest\n", "import unittest\nfrom unittest.mock import patch\n", 1)
marker = '\n\nif __name__ == "__main__":\n    unittest.main()\n'
addition = r'''

    def test_release_crawl_uses_proven_single_page_size(self):
        self.assertEqual(5000, crawler.PAGE_SIZE)
        payload = {
            "content": [
                {"identifier": {"functionalId": "100"}, "title": "One", "lang": "de", "market": "GS_DE"},
                {"identifier": {"functionalId": "200"}, "title": "Two", "lang": "de", "market": "GS_DE"},
            ],
            "page": {"number": 0, "size": 5000, "totalElements": 2, "totalPages": 1},
        }
        with patch.object(crawler, "_headers", return_value=[]), patch.object(
            crawler.catalog, "_http_json", return_value=(payload, "app")
        ) as request:
            rows = crawler._search_catalog(
                {"platform_base_url": "https://example.invalid"}, {}, {},
                language="de", country="DE", configured_language="de", configured_country="DE"
            )
        self.assertEqual(["100", "200"], [row["variantId"] for row in rows])
        self.assertEqual(5000, request.call_args.kwargs["params"]["size"])
        self.assertEqual(0, request.call_args.kwargs["params"]["page"])

    def test_release_crawl_fails_if_single_page_contract_is_exceeded(self):
        payload = {"content": [], "page": {"number": 0, "size": 5000, "totalElements": 5001, "totalPages": 2}}
        with patch.object(crawler, "_headers", return_value=[]), patch.object(
            crawler.catalog, "_http_json", return_value=(payload, "app")
        ):
            with self.assertRaisesRegex(RuntimeError, "exceeds proven single-page"):
                crawler._search_catalog(
                    {"platform_base_url": "https://example.invalid"}, {}, {},
                    language="de", country="DE", configured_language="de", configured_country="DE"
                )

    def test_release_crawl_fails_on_total_or_identity_drift(self):
        mismatch = {
            "content": [{"identifier": {"functionalId": "100"}}],
            "page": {"number": 0, "size": 5000, "totalElements": 2, "totalPages": 1},
        }
        with patch.object(crawler, "_headers", return_value=[]), patch.object(
            crawler.catalog, "_http_json", return_value=(mismatch, "app")
        ):
            with self.assertRaisesRegex(RuntimeError, "row count does not match"):
                crawler._search_catalog(
                    {"platform_base_url": "https://example.invalid"}, {}, {},
                    language="de", country="DE", configured_language="de", configured_country="DE"
                )
        duplicate = {
            "content": [
                {"identifier": {"functionalId": "100"}},
                {"identifier": {"functionalId": "100"}},
            ],
            "page": {"number": 0, "size": 5000, "totalElements": 2, "totalPages": 1},
        }
        with patch.object(crawler, "_headers", return_value=[]), patch.object(
            crawler.catalog, "_http_json", return_value=(duplicate, "app")
        ):
            with self.assertRaisesRegex(RuntimeError, "duplicate provider functional IDs"):
                crawler._search_catalog(
                    {"platform_base_url": "https://example.invalid"}, {}, {},
                    language="de", country="DE", configured_language="de", configured_country="DE"
                )
'''
if marker not in tests:
    raise SystemExit("unittest footer not found")
tests = tests.replace(marker, addition + marker, 1)
test_path.write_text(tests, encoding="utf-8")
