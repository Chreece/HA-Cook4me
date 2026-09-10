#!/usr/bin/env python3
"""Temporary maintenance patch: align legacy release builder with proven single-page crawl."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "tools" / "build_release_catalog.py"
text = path.read_text(encoding="utf-8")
if "PAGE_SIZE = 50\n" not in text:
    raise SystemExit("legacy builder PAGE_SIZE=50 marker not found")
text = text.replace("PAGE_SIZE = 50\n", "PAGE_SIZE = 5000\n", 1)
start = text.index("def _all_search_rows(\n")
end = text.index("\ndef _detail(\n", start)
replacement = '''def _all_search_rows(
    cfg,
    tokens,
    pcfg,
    *,
    language: str,
    country: str,
    configured_language: str,
    configured_country: str,
) -> list[dict[str, Any]]:
    """Return one complete stable provider manifest page or fail closed.

    A credential-free all-28 probe on 2026-09-10 proved that page=0,size=5000
    returns every current Cookeo BRAND publication in each audited mapping with
    stable repeated provider-ID sets. Smaller paged walks drifted between
    identical requests. Never silently fall back to unstable pagination here.
    """
    market = f"GS_{country}"
    url = cfg["platform_base_url"].rstrip("/") + "/common-api/v4/search/recipes"
    payload, _auth = catalog._http_json(
        "POST",
        url,
        headers_iter=_headers(
            cfg,
            tokens,
            configured_country,
            configured_language,
            url,
            pcfg,
        ),
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
        body=app_search_body(language, market),
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
        row = catalog._light_search_row(raw)
        if not row:
            raise RuntimeError(f"{language}/{market}: recipe search row could not be normalized")
        variant_id = _text(row.get("searchVariantId"))
        if not variant_id:
            raise RuntimeError(f"{language}/{market}: recipe search row is missing provider identity")
        rows.append(row)
    ids = [_text(row.get("searchVariantId")) for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError(
            f"{language}/{market}: duplicate provider functional IDs in proven single-page response"
        )
    return rows
'''
text = text[:start] + replacement + text[end:]
path.write_text(text, encoding="utf-8")

test_path = ROOT / "tests" / "test_v59_architecture_contract.py"
tests = test_path.read_text(encoding="utf-8")
old = '''        self.assertIn("while total_pages is None or page < total_pages", builder)\n        self.assertIn("hydratedVariants", builder)\n'''
new = '''        self.assertIn("PAGE_SIZE = 5000", builder)\n        self.assertIn("provider catalog exceeds proven single-page", builder)\n        self.assertIn("single-page response row count does not match provider total", builder)\n        self.assertIn("duplicate provider functional IDs", builder)\n        self.assertNotIn("while total_pages is None or page < total_pages", builder)\n        self.assertIn("hydratedVariants", builder)\n'''
if old not in tests:
    raise SystemExit("v59 architecture paging assertion marker not found")
tests = tests.replace(old, new, 1)
test_path.write_text(tests, encoding="utf-8")
