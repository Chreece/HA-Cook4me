"""Country-scoped observed prices and automatic recipe costing.

Read-only Open Prices API; no receipt uploads, retailer scraping or AI-made prices.
"""
from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
from functools import partial
import time

from .currency_markets import COUNTRY_CURRENCIES, CURRENCIES
from .costs import _cost_for_amount, _country, _currency, _number, cost_store_for_bridge, lookup_open_prices
from .inventory import inventory_identity, convert_amount
from .recipe_cost_cache import recipe_cost_cache_for_bridge

# Exact English catalog names only. Prepared/mixed foods are never collapsed into
# a raw ingredient by fuzzy matching. Category matches remain estimates.
_CATEGORIES = {}
for tag, kind, names in (
    ('tomatoes', 'CATEGORY', 'tomato|tomatoes'), ('potatoes', 'CATEGORY', 'potato|potatoes'),
    ('onions', 'CATEGORY', 'onion|onions'), ('carrots', 'CATEGORY', 'carrot|carrots'),
    ('courgettes', 'CATEGORY', 'courgette|courgettes|zucchini'), ('aubergines', 'CATEGORY', 'aubergine|aubergines|eggplant'),
    ('broccoli', 'CATEGORY', 'broccoli'), ('cauliflowers', 'CATEGORY', 'cauliflower'),
    ('cucumbers', 'CATEGORY', 'cucumber|cucumbers'), ('leeks', 'CATEGORY', 'leek|leeks'),
    ('spinachs', 'CATEGORY', 'spinach'), ('garlic', 'CATEGORY', 'garlic'),
    ('lemons', 'CATEGORY', 'lemon|lemons'), ('apples', 'CATEGORY', 'apple|apples'),
    ('bananas', 'CATEGORY', 'banana|bananas'), ('oranges', 'CATEGORY', 'orange|oranges'),
    ('rices', 'PRODUCT', 'rice'), ('basmati-rices', 'PRODUCT', 'basmati rice'),
    ('pastas', 'PRODUCT', 'pasta'), ('spaghetti', 'PRODUCT', 'spaghetti'),
    ('olive-oils', 'PRODUCT', 'olive oil'), ('sunflower-oils', 'PRODUCT', 'sunflower oil'),
    ('butters', 'PRODUCT', 'butter'), ('milks', 'PRODUCT', 'milk'),
    ('wheat-flours', 'PRODUCT', 'wheat flour'), ('sugars', 'PRODUCT', 'sugar'),
    ('salts', 'PRODUCT', 'salt'), ('eggs', 'PRODUCT', 'egg|eggs'),
    ('red-lentils', 'PRODUCT', 'red lentils'), ('green-lentils', 'PRODUCT', 'green lentils'),
    ('chickpeas', 'PRODUCT', 'chickpea|chickpeas'), ('tofu', 'PRODUCT', 'tofu'),
):
    for name in names.split('|'):
        _CATEGORIES[name] = ('en:' + tag, kind)


def country_currency(country):
    return next(iter(COUNTRY_CURRENCIES.get(country, [])), '')


def validate_market(country, currency):
    if country not in COUNTRY_CURRENCIES or currency not in CURRENCIES:
        raise ValueError('Choose a valid country and currency')


async def price_settings(bridge):
    store = await cost_store_for_bridge(bridge)
    settings = store.settings
    country = settings.get('country') or _country(getattr(bridge.hass.config, 'country', ''))
    currency = settings.get('currency') or country_currency(country)
    if country != settings.get('country') or currency != settings.get('currency'):
        await store.async_set_settings(country=country, currency=currency)
    return store.settings


def category_for(ingredient):
    if not isinstance(ingredient, dict):
        return None
    # Callers supply the server catalog row, never a model's category guess.
    name = str(ingredient.get('canonicalName') or ingredient.get('name') or '').strip().casefold()
    return _CATEGORIES.get(name)


def canonical_recipe(recipe, catalog):
    lookup = {}
    for row in catalog:
        for key in (row.get('key'), row.get('foodKey'), row.get('id'), row.get('ingredientId')):
            if key:
                lookup[str(key)] = row
    result = deepcopy(recipe)
    rows = []
    for raw in recipe.get('ingredients') or []:
        if not isinstance(raw, dict):
            rows.append({'name': str(raw)})
            continue
        key = str(raw.get('key') or raw.get('foodKey') or raw.get('ingredientId') or '')
        match = lookup.get(key, {})
        rows.append({**raw, **({'key': match.get('key') or match.get('ingredientId') or match.get('id') or key} if key else {}),
                     'name': raw.get('name') or raw.get('foodName') or match.get('name') or key,
                     'canonicalName': match.get('canonicalName') or match.get('name') or raw.get('canonicalName') or raw.get('name') or raw.get('foodName')})
    result['ingredients'] = rows
    return result


def _fresh(reference):
    if not reference:
        return False
    if not str(reference.get('source', '')).startswith('open_prices'):
        return True
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(reference['updatedAt'])).total_seconds() < 86400
    except (KeyError, TypeError, ValueError):
        return False


async def _observations(bridge, *, barcode='', category='', category_type='CATEGORY', settings):
    """Coalesce repeated requests; bound concurrency and cache misses for an hour."""
    if not hasattr(bridge, '_price_queries'):
        bridge._price_queries = {}
        bridge._price_query_lock = asyncio.Lock()
        bridge._price_slots = asyncio.Semaphore(3)
    key = (barcode, category, category_type, settings['country'], settings['currency'])
    async with bridge._price_query_lock:
        cached = bridge._price_queries.get(key)
        if cached and cached[0] > time.monotonic():
            task = cached[1]
        else:
            async def fetch():
                async with bridge._price_slots:
                    result = await bridge.hass.async_add_executor_job(partial(lookup_open_prices, barcode,
                        category=category, category_type=category_type,
                        country=settings['country'], currency=settings['currency']))
                    if not result.get('ok'):
                        cached_query = bridge._price_queries.get(key)
                        if cached_query and cached_query[1] is asyncio.current_task():
                            bridge._price_queries[key] = (time.monotonic() + 60, cached_query[1])
                    return result
            task = bridge.hass.async_create_background_task(fetch(), 'Cook4Me price observation')
            bridge._price_queries[key] = (time.monotonic() + 3600, task)
            while len(bridge._price_queries) > 500:
                bridge._price_queries.pop(next(iter(bridge._price_queries)))
    return deepcopy(await asyncio.shield(task))


async def _store_observation(store, identity, row, *, generic=False):
    source = 'open_prices_category' if generic else 'open_prices'
    existing = next((ref for ref in store._data.get('references', {}).values()
                     if ref.get('identity') == identity and ref.get('source') == source
                     and ref.get('country') == row['country'] and ref.get('currency') == row['currency']), None)
    if _fresh(existing) and all(existing.get(key) == row.get(key) for key in
            ('amount', 'currency', 'basisQuantity', 'basisUnit', 'country', 'location', 'date', 'barcode')) \
            and existing.get('observationId') == (row.get('id') or row.get('observationId')):
        return deepcopy(existing)
    return await store.async_set_reference(identity, amount=row['amount'], currency=row['currency'],
        basis_quantity=row['basisQuantity'], basis_unit=row['basisUnit'],
        source='open_prices_category' if generic else 'open_prices', confidence='external_observation',
        country=row['country'], location=row.get('location', ''), date=row.get('date', ''),
        barcode=row.get('barcode', ''), observation_id=row.get('id') or row.get('observationId'))


async def product_price(bridge, *, barcode='', ingredient=None, quantity=None, unit='', settings=None):
    settings = settings or await price_settings(bridge)
    store = await cost_store_for_bridge(bridge)
    country, currency = settings['country'], settings['currency']
    identity = inventory_identity(ingredient) if ingredient else ''
    reference = store.barcode_reference(barcode, country=country, currency=currency) if barcode else None
    kind = 'barcode'
    fallback = store.best_reference(identity, country=country, currency=currency) if identity else None
    reason = 'no_observation'
    if settings.get('autoGlobalPrices') and country and currency:
        async def lookup(**kwargs):
            nonlocal reason
            data = await _observations(bridge, settings=settings, **kwargs)
            if not data.get('ok'):
                reason = 'source_unavailable'
            rows = [row for row in data.get('items', []) if row.get('usable')
                    and row.get('country') == country and row.get('currency') == currency
                    and (not unit or convert_amount(1, unit, row.get('basisUnit')) is not None)]
            return max(rows, key=lambda row: row.get('date', ''), default=None)
        if barcode and not _fresh(reference):
            row = await lookup(barcode=barcode)
            if row:
                reference = await _store_observation(store, 'barcode:' + barcode, row)
        if reference is None and not _fresh(fallback):
            category = category_for(ingredient)
            if category:
                row = await lookup(category=category[0], category_type=category[1])
                if row:
                    fallback = await _store_observation(store, identity, row, generic=True)
    elif not country or not currency:
        reason = 'choose_country'
    else:
        reason = 'automatic_disabled'
    if reference is None:
        reference, kind = fallback, 'ingredient'
    amount = _cost_for_amount(reference, quantity, unit) if reference else None
    return {'settings': settings, 'reference': reference, 'matchKind': kind,
            'estimate': round(amount, 2) if amount is not None else None,
            'status': 'priced' if amount is not None else 'basis_missing' if reference else reason}


def validate_paid_price(raw):
    if raw is None:
        return None
    amount = _number(raw.get('amount'))
    currency = _currency(raw.get('currency'))
    if amount is None or currency not in CURRENCIES:
        raise ValueError('Enter a non-negative price and a three-letter currency')
    return {'amount': amount, 'currency': currency, 'country': _country(raw.get('country')),
            'location': str(raw.get('location') or '')[:300]}


async def save_product_prices(bridge, ingredient, lot_id, msg, metadata):
    """Only an explicitly entered paid amount is exact; observations stay estimates."""
    store = await cost_store_for_bridge(bridge)
    settings = await price_settings(bridge)
    paid = validate_paid_price(msg.get('paid_price'))
    identity = inventory_identity(ingredient)
    if paid:
        args = dict(amount=paid['amount'], currency=paid['currency'], basis_quantity=msg['quantity'],
            basis_unit=msg['unit'], country=paid['country'] or settings['country'], location=paid['location'],
            date=metadata.get('purchaseDate') or datetime.now(timezone.utc).date().isoformat(), barcode=metadata.get('barcode', ''))
        await store.async_set_reference('lot:' + lot_id, **args, source='purchase', confidence='exact_purchase')
        # The same purchase is an estimate for future quantities, not another paid lot.
        await store.async_set_reference(identity, **args, source='purchase_reference', confidence='user_entered')
    elif metadata.get('barcode'):
        reference = store.barcode_reference(metadata['barcode'], country=settings['country'], currency=settings['currency'])
        if reference:
            await _store_observation(store, identity, reference)


async def recipe_price(bridge, recipe, catalog):
    settings = await price_settings(bridge)
    store = await cost_store_for_bridge(bridge)
    recipe = canonical_recipe(recipe, catalog)
    inventory = bridge.recipe_hub.profile.get('houseIngredients') or []
    tasks, seen = [], set()
    for item in recipe.get('ingredients', []):
        identity = inventory_identity(item)
        if identity in seen:
            continue
        seen.add(identity)
        codes = {lot.get('barcode') for row in inventory if inventory_identity(row) == identity
                 for lot in row.get('lots', []) if lot.get('barcode')}
        if not codes:
            # Confirmed product->ingredient evidence remains usable after stock is consumed.
            ref = store.best_reference(identity, country=settings['country'], currency=settings['currency'])
            codes = {ref['barcode']} if ref and ref.get('barcode') else {''}
        for code in sorted(codes):
            if len(tasks) >= 24:
                break
            async def hydrate(item=item, code=code, identity=identity):
                result = await product_price(bridge, barcode=code, ingredient=item,
                    unit=item.get('unit') or (item.get('weight') or {}).get('unit', ''), settings=settings)
                # Stock barcodes and saved ingredient links are confirmed mappings.
                # Preserve a fresh generic estimate when the last package is gone.
                if result.get('reference') and result.get('matchKind') == 'barcode':
                    await _store_observation(store, identity, result['reference'])
                return result
            tasks.append(hydrate())
    failures = 0
    try:
        async with asyncio.timeout(30):
            results = await asyncio.gather(*tasks, return_exceptions=True)
            failures = sum(isinstance(result, Exception) or result.get('status') == 'source_unavailable' for result in results)
    except TimeoutError:
        failures = 1
    cache = await recipe_cost_cache_for_bridge(bridge)
    cost = await cache.async_cost(recipe, inventory, store, country=settings['country'], currency=settings['currency'])
    cost.update(settings=settings, priceLookupIncomplete=bool(failures), priceSource='Open Prices',
                originalIngredients=True, ingredientLimitReached=len(seen) > 24)
    return cost
