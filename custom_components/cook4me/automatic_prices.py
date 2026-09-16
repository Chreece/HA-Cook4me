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
    ('zucchini', 'CATEGORY', 'courgette|courgettes|zucchini'), ('aubergines', 'CATEGORY', 'aubergine|aubergines|eggplant'),
    ('broccoli', 'CATEGORY', 'broccoli'), ('cauliflowers', 'CATEGORY', 'cauliflower'),
    ('cucumbers', 'CATEGORY', 'cucumber|cucumbers'), ('leeks', 'CATEGORY', 'leek|leeks'),
    ('spinachs', 'CATEGORY', 'spinach'), ('garlics', 'CATEGORY', 'garlic'),
    ('lemons', 'CATEGORY', 'lemon|lemons'), ('apples', 'CATEGORY', 'apple|apples'),
    ('bananas', 'CATEGORY', 'banana|bananas'), ('oranges', 'CATEGORY', 'orange|oranges'),
    ('rices', 'PRODUCT', 'rice'), ('basmati-rices', 'PRODUCT', 'basmati rice'),
    ('pastas', 'PRODUCT', 'pasta'), ('spaghetti', 'PRODUCT', 'spaghetti'),
    ('olive-oils', 'PRODUCT', 'olive oil'), ('sunflower-oils', 'PRODUCT', 'sunflower oil'),
    ('butters', 'PRODUCT', 'butter'), ('milks', 'PRODUCT', 'milk'),
    ('wheat-flours', 'PRODUCT', 'wheat flour'), ('sugars', 'PRODUCT', 'sugar'),
    ('salts', 'PRODUCT', 'salt'), ('eggs', 'PRODUCT', 'egg|eggs'),
    ('red-lentils', 'PRODUCT', 'red lentils'), ('green-lentils', 'PRODUCT', 'green lentils'),
    ('chickpeas', 'PRODUCT', 'chickpea|chickpeas'), ('plain-tofu', 'PRODUCT', 'tofu'),
    # Explicit food forms verified against the Open Food Facts taxonomy.
    ('wheat-flours', 'PRODUCT', 'all-purpose flour|plain flour'),
    ('extra-virgin-olive-oils', 'PRODUCT', 'extra virgin olive oil|extra-virgin olive oil'),
    ('brown-rices', 'PRODUCT', 'brown rice'), ('jasmine-rice', 'PRODUCT', 'jasmine rice'),
    ('rices-for-risotto', 'PRODUCT', 'risotto rice|arborio rice|carnaroli rice'),
    ('lentils', 'PRODUCT', 'lentils|dried lentils'),
    ('canned-lentils', 'PRODUCT', 'canned lentils|canned cooked lentils'),
    ('canned-chickpeas', 'PRODUCT', 'canned chickpeas'),
    ('canned-tomatoes', 'PRODUCT', 'canned tomatoes|canned chopped tomatoes|chopped canned tomatoes'),
    ('tomato-pastes', 'PRODUCT', 'tomato paste'),
    ('coconut-milks', 'PRODUCT', 'coconut milk'),
    ('yogurts', 'PRODUCT', 'yogurt|yoghurt|plain yogurt|plain yoghurt'),
    ('greek-style-yogurts-plain', 'PRODUCT', 'greek yogurt|greek yoghurt'),
    ('creams', 'PRODUCT', 'cream|cooking cream'),
    ('feta', 'PRODUCT', 'feta|feta cheese'), ('mozzarella', 'PRODUCT', 'mozzarella'),
    ('cheddar-cheese', 'PRODUCT', 'cheddar|cheddar cheese'),
    ('honeys', 'PRODUCT', 'honey'), ('soy-sauces', 'PRODUCT', 'soy sauce'),
    ('ground-black-peppers', 'PRODUCT', 'ground black pepper'),
    ('paprika', 'PRODUCT', 'paprika'), ('cumin', 'PRODUCT', 'cumin'),
    ('mushrooms', 'CATEGORY', 'mushroom|mushrooms|button mushroom|button mushrooms'),
    ('sweet-potatoes', 'CATEGORY', 'sweet potato|sweet potatoes'),
    ('green-peas', 'CATEGORY', 'green peas|fresh peas'),
    ('green-beans', 'CATEGORY', 'green bean|green beans'),
    ('red-bell-peppers', 'CATEGORY', 'red bell pepper|red bell peppers'),
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
        key = str(raw.get('key') or raw.get('foodKey') or raw.get('ingredientId') or raw.get('id') or '')
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


async def _observations(bridge, *, barcode='', category='', category_type='CATEGORY', settings, refresh_since=None):
    """Coalesce repeated requests; bound concurrency and cache misses for an hour."""
    if not hasattr(bridge, '_price_queries'):
        bridge._price_queries = {}
        bridge._price_query_lock = asyncio.Lock()
        bridge._price_slots = asyncio.Semaphore(3)
    key = (barcode, category, category_type, settings['country'], settings['currency'])
    async with bridge._price_query_lock:
        cached = bridge._price_queries.get(key)
        if cached and (not cached[1].done() or (cached[0] > time.monotonic() and
                (refresh_since is None or len(cached) > 2 and cached[2] >= refresh_since))):
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
                            bridge._price_queries[key] = (time.monotonic() + 60, cached_query[1], cached_query[2])
                    return result
            task = bridge.hass.async_create_background_task(fetch(), 'Cook4Me price observation')
            bridge._price_queries[key] = (time.monotonic() + 3600, task, time.monotonic())
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


async def product_price(bridge, *, barcode='', ingredient=None, quantity=None, unit='', settings=None, refresh_since=None):
    settings = settings or await price_settings(bridge)
    store = await cost_store_for_bridge(bridge)
    country, currency = settings['country'], settings['currency']
    identity = inventory_identity(ingredient) if ingredient else ''
    reference = store.barcode_reference(barcode, country=country, currency=currency) if barcode else None
    kind = 'barcode'
    fallback = store.best_reference(identity, country=country, currency=currency) if identity else None
    if reference is None and barcode and fallback and fallback.get('barcode') == barcode:
        reference = fallback
    reason = 'no_observation'
    lookup_failed = False
    if (settings.get('autoGlobalPrices') or refresh_since is not None) and country and currency:
        async def lookup(**kwargs):
            nonlocal reason, lookup_failed
            data = await _observations(bridge, settings=settings, refresh_since=refresh_since, **kwargs)
            if not data.get('ok'):
                reason = 'source_unavailable'
                lookup_failed = True
            rows = [row for row in data.get('items', []) if row.get('usable')
                    and row.get('country') == country and row.get('currency') == currency
                    and (not unit or convert_amount(1, unit, row.get('basisUnit')) is not None)]
            if not rows and any(row.get('usable') for row in data.get('items', [])) and not lookup_failed:
                reason = 'basis_missing'
            return max(rows, key=lambda row: row.get('date', ''), default=None)
        if barcode and (refresh_since is not None or not _fresh(reference)):
            row = await lookup(barcode=barcode)
            if row:
                await _store_observation(store, 'barcode:' + barcode, row)
                reference = store.barcode_reference(barcode, country=country, currency=currency)
        if reference is None and (refresh_since is not None or not _fresh(fallback)):
            category = category_for(ingredient)
            if category:
                row = await lookup(category=category[0], category_type=category[1])
                if row:
                    await _store_observation(store, identity, row, generic=True)
                    fallback = store.best_reference(identity, country=country, currency=currency)
            elif not barcode and fallback is None:
                reason = 'category_unmapped'
    elif not country or not currency:
        reason = 'choose_country'
    else:
        reason = 'automatic_disabled'
    if reference is None:
        reference, kind = fallback, 'ingredient'
    amount = _cost_for_amount(reference, quantity, unit) if reference else None
    return {'settings': settings, 'reference': reference, 'matchKind': kind,
            'estimate': round(amount, 2) if amount is not None else None, 'lookupFailed': lookup_failed,
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


async def recipe_price(bridge, recipe, catalog, *, refresh_since=None):
    settings = await price_settings(bridge)
    store = await cost_store_for_bridge(bridge)
    recipe = canonical_recipe(recipe, catalog)
    inventory = bridge.recipe_hub.profile.get('houseIngredients') or []
    tasks, seen, lookup_status = [], set(), {}
    skipped = False
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
                skipped = True
                lookup_status.setdefault(identity, 'lookup_limit')
                break
            async def hydrate(item=item, code=code, identity=identity):
                result = await product_price(bridge, barcode=code, ingredient=item,
                    unit=item.get('unit') or (item.get('weight') or {}).get('unit', ''), settings=settings,
                    refresh_since=refresh_since)
                lookup_status[identity] = result.get('status')
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
            failures = sum(isinstance(result, Exception) or result.get('lookupFailed') or result.get('status') == 'source_unavailable' for result in results)
    except TimeoutError:
        failures = 1
    cache = await recipe_cost_cache_for_bridge(bridge)
    cost = await cache.async_cost(recipe, inventory, store, country=settings['country'], currency=settings['currency'], force=refresh_since is not None)
    for row in cost.get('ingredients', []):
        if row.get('coverage', 0) < 1:
            row['priceStatus'] = ('recipe_amount_unknown' if row.get('reason') == 'recipe_amount_unknown'
                                  else lookup_status.get(row['identity']) or ('source_unavailable' if failures else 'no_observation'))
    cost.update(settings=settings, priceLookupIncomplete=bool(failures), priceSource='Open Prices',
                originalIngredients=True, ingredientLimitReached=skipped,
                checkedAt=datetime.now(timezone.utc).isoformat(), refreshed=refresh_since is not None,
                refreshPolicy={'observationsSeconds': 86400, 'missSeconds': 3600, 'failureSeconds': 60,
                               'onDemand': True, 'maximumObservationDays': 180})
    return cost
