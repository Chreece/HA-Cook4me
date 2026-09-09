from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "custom_components" / "cook4me" / "recipe_cost_cache.py"
WS31 = ROOT / "custom_components" / "cook4me" / "websocket_v31.py"
V60 = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v60.js"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_recipe_cost_cache_fingerprints_only_relevant_price_evidence():
    text = _text(CACHE)
    assert "pricing_fingerprint" in text
    assert '"lotReference"' in text
    assert 'cost_store.best_reference(f"lot:{lot_id}")' in text
    assert '"barcodeReference"' in text
    assert 'cost_store.best_reference(identity, currency=currency, country=country)' in text
    assert '"priceFingerprint"' in text
    assert '"relevant-price-fingerprint-v1"' in text


def test_manual_price_refresh_bypasses_automatic_cache_throttle():
    text = _text(WS31)
    assert "lookup_open_prices_safe(" in text
    assert "await cache.async_record(cache_key, result, source=\"open_prices\")" in text
    assert "store_best_open_price(" in text
    assert 'result["forcedGlobalRefresh"] = bool(forced)' in text
    assert "calculate_recipe_cost(recipe, inventory, cost_store)" in text
    assert "_hydrate_global_prices_cached" in text
    assert "_recipe_cost_with_store" not in text


def test_active_frontend_routes_recipe_cost_to_v31():
    text = _text(V60)
    assert '"cook4me/v31/recipe_cost"' in text
    assert 'requested==="cook4me/v20/recipe_cost"' in text
    assert 'requested==="cook4me/v23/recipe_cost"' in text
    assert 'requested==="cook4me/v30/recipe_cost"' in text
