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
from .price_units import price_ingredient

# Exact English catalog names only. Prepared/mixed foods are never collapsed into
# a raw ingredient by fuzzy matching. Category matches remain estimates.
_RECIPE_WAIT_SECONDS = 20
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
    # v84: frequent release-catalog names, checked against the OFF taxonomy.
    ('ginger', 'CATEGORY', 'ginger'),
    ('parsley', 'CATEGORY', 'parsley'),
    ('shallots', 'CATEGORY', 'shallot'),
    ('basils', 'CATEGORY', 'basil'),
    ('mint', 'CATEGORY', 'mint'),
    ('limes', 'CATEGORY', 'lime'),
    ('thyme', 'CATEGORY', 'thyme'),
    ('asparagus', 'CATEGORY', 'asparagus'),
    ('celery', 'CATEGORY', 'celery'),
    ('pears', 'CATEGORY', 'pear'),
    ('chives', 'CATEGORY', 'chives'),
    ('almonds', 'CATEGORY', 'almond'),
    ('cherry-tomatoes', 'CATEGORY', 'cherry tomato'),
    ('beetroot', 'CATEGORY', 'beetroot'),
    ('fennel', 'CATEGORY', 'fennel'),
    ('turnip', 'CATEGORY', 'turnip'),
    ('dill', 'CATEGORY', 'dill'),
    ('pine-nuts', 'CATEGORY', 'pine nut'),
    ('cabbages', 'CATEGORY', 'cabbage'),
    ('strawberries', 'CATEGORY', 'strawberry'),
    ('pineapples', 'CATEGORY', 'pineapple'),
    ('walnuts', 'CATEGORY', 'walnut'),
    ('pumpkins', 'CATEGORY', 'pumpkin'),
    ('celeriac', 'CATEGORY', 'celeriac'),
    ('green-cabbage', 'CATEGORY', 'green cabbage'),
    ('rosemary', 'CATEGORY', 'rosemary'),
    ('peaches', 'CATEGORY', 'peach'),
    ('oregano', 'CATEGORY', 'oregano'),
    ('sage', 'CATEGORY', 'sage'),
    ('chestnuts', 'CATEGORY', 'chestnut'),
    ('avocados', 'CATEGORY', 'avocado'),
    ('mangoes', 'CATEGORY', 'mango'),
    ('raspberries', 'CATEGORY', 'raspberry'),
    ('butternut-squashes', 'CATEGORY', 'butternut squash'),
    ('shiitake-mushrooms', 'CATEGORY', 'shiitake mushroom'),
    ('green-asparagus', 'CATEGORY', 'green asparagus'),
    ('tarragon', 'CATEGORY', 'tarragon'),
    ('pistachios', 'CATEGORY', 'pistachio'),
    ('cashew-nuts', 'CATEGORY', 'cashew nut'),
    ('brussels-sprouts', 'CATEGORY', 'brussels sprouts'),
    ('lettuces', 'CATEGORY', 'lettuce'),
    ('dates', 'CATEGORY', 'date'),
    ('red-cabbage', 'CATEGORY', 'red cabbage'),
    ('blueberries', 'CATEGORY', 'blueberry'),
    ('parsnip', 'CATEGORY', 'parsnip'),
    ('chards', 'CATEGORY', 'chard'),
    ('hazelnuts', 'CATEGORY', 'hazelnut'),
    ('radishes', 'CATEGORY', 'radish'),
    ('rocket', 'CATEGORY', 'rocket'),
    ('lemon-zest', 'CATEGORY', 'lemon zest'),
    ('white-wines', 'PRODUCT', 'white wine'),
    ('lemon-juice', 'PRODUCT', 'lemon juice'),
    ('beef', 'PRODUCT', 'beef'),
    ('tomato-purees', 'PRODUCT', 'tomato purée'),
    ('cinnamon', 'PRODUCT', 'cinnamon'),
    ('baking-powders', 'PRODUCT', 'baking powder'),
    ('prawns', 'PRODUCT', 'prawns'),
    ('turmeric', 'PRODUCT', 'turmeric'),
    ('sesame-oils', 'PRODUCT', 'sesame oil'),
    ('egg-yolk', 'PRODUCT', 'egg yolk'),
    ('pork', 'PRODUCT', 'pork'),
    ('chicken-thighs', 'PRODUCT', 'chicken thigh'),
    ('mustards', 'PRODUCT', 'mustard'),
    ('salmons', 'PRODUCT', 'salmon'),
    ('mixed-herbs', 'PRODUCT', 'mixed herbs'),
    ('chocolates', 'PRODUCT', 'chocolate'),
    ('breads', 'PRODUCT', 'bread'),
    ('brown-sugars', 'PRODUCT', 'brown sugar'),
    ('chicken-breasts', 'PRODUCT', 'chicken breast'),
    ('red-wines', 'PRODUCT', 'red wine'),
    ('raisins', 'PRODUCT', 'raisin'),
    ('hams', 'PRODUCT', 'ham'),
    ('bacon', 'PRODUCT', 'bacon'),
    ('quinoa', 'PRODUCT', 'quinoa'),
    ('corn-starch', 'PRODUCT', 'corn starch'),
    ('nutmeg', 'PRODUCT', 'nutmeg'),
    ('black-olives', 'PRODUCT', 'black olive'),
    ('vanilla-pods', 'PRODUCT', 'vanilla pod'),
    ('whipped-creams', 'PRODUCT', 'whipped cream'),
    ('saffron', 'PRODUCT', 'saffron'),
    ('tomato-sauces', 'PRODUCT', 'tomato sauce'),
    ('green-olives', 'PRODUCT', 'green olive'),
    ('cider-vinegars', 'PRODUCT', 'cider vinegar'),
    ('vanilla', 'PRODUCT', 'vanilla'),
    ('curry-pastes', 'PRODUCT', 'curry paste'),
    ('sour-creams', 'PRODUCT', 'sour cream'),
    ('orange-juices', 'PRODUCT', 'orange juice'),
    ('mascarpone', 'PRODUCT', 'mascarpone'),
    ('ricotta', 'PRODUCT', 'ricotta'),
    ('mayonnaises', 'PRODUCT', 'mayonnaise'),
    ('vinegars', 'PRODUCT', 'vinegar'),
    ('cods', 'PRODUCT', 'cod'),
    ('rice-vinegars', 'PRODUCT', 'rice vinegar'),
    ('tomato-ketchup', 'PRODUCT', 'tomato ketchup'),
    ('caramels', 'PRODUCT', 'caramel'),
    ('egg-white', 'PRODUCT', 'egg white'),
    ('sausages', 'PRODUCT', 'sausage'),
    ('tunas', 'PRODUCT', 'tuna'),
    ('ground-almonds', 'PRODUCT', 'ground almonds'),
    ('olives', 'PRODUCT', 'olive'),
    ('mussels', 'PRODUCT', 'mussels'),
    ('capers', 'PRODUCT', 'caper'),
    ('chorizo', 'PRODUCT', 'chorizo'),
    ('mirin', 'PRODUCT', 'mirin'),
    ('biscuits', 'PRODUCT', 'biscuit'),
    ('whole-milks', 'PRODUCT', 'whole milk'),
    ('dried-tomatoes', 'PRODUCT', 'dried tomato'),
    ('yeast', 'PRODUCT', 'yeast'),
    ('condensed-milks', 'PRODUCT', 'condensed milk'),
    ('pestos', 'PRODUCT', 'pesto'),
    ('beers', 'PRODUCT', 'beer'),
    ('buckwheat', 'PRODUCT', 'buckwheat'),
    ('herbes-de-provence', 'PRODUCT', 'herbes de provence'),
    ('coconut-oils', 'PRODUCT', 'coconut oil'),
    ('pumpkin-seeds', 'PRODUCT', 'pumpkin seeds'),
    ('gnocchi', 'PRODUCT', 'gnocchi'),
    ('cloves', 'PRODUCT', 'clove'),
    ('lamb-shoulder', 'PRODUCT', 'lamb shoulder'),
    ('margarines', 'PRODUCT', 'margarine'),
    ('balsamic-vinegars', 'PRODUCT', 'balsamic vinegar'),
    ('fresh-goat-cheese', 'PRODUCT', 'fresh goat cheese'),
    ('chickens', 'PRODUCT', 'chicken'),
    ('rolled-oats', 'PRODUCT', 'rolled oats'),
    ('peanut-butters', 'PRODUCT', 'peanut butter'),
    ('chicken-drumsticks', 'PRODUCT', 'chicken drumstick'),
    ('oyster-sauces', 'PRODUCT', 'oyster sauce'),
    ('misos', 'PRODUCT', 'miso'),
    ('tahini', 'PRODUCT', 'tahini'),
    ('smoked-bacon', 'PRODUCT', 'smoked bacon'),
    ('maple-syrups', 'PRODUCT', 'maple syrup'),
    ('croutons', 'PRODUCT', 'crouton'),
    ('butters', 'PRODUCT', 'salted butter & unsalted butter|salted butter|unsalted butter'),
    ('wheat-flours', 'PRODUCT', 'flour'),
    ('potatoes', 'CATEGORY', 'white potatoes'),
    ('cremes-fraiches', 'PRODUCT', 'crème fraîche|creme fraiche|thick crème fraîche'),
    ('creams', 'PRODUCT', 'liquid cream'),
    ('scallions', 'CATEGORY', 'spring onion|spring onions|welsh onion'),
    ('powdered-sugars', 'PRODUCT', 'icing sugar|powdered sugar'),
    ('bread-crumbs', 'PRODUCT', 'breadcrumbs|bread crumbs'),
    ('lamb-meat', 'PRODUCT', 'lamb'),
    ('ground-beef-meats', 'PRODUCT', 'minced beef|ground beef'),
    ('sesame', 'PRODUCT', 'sesame seed|sesame seeds'),
    ('nuoc-mam-sauce', 'PRODUCT', 'fish sauce'),
    ('peanut-oils', 'PRODUCT', 'groundnut oil|peanut oil'),
    ('scallop', 'PRODUCT', 'scallops'),
    ('corn-starch', 'PRODUCT', 'cornflour'),
    ('bulgur', 'PRODUCT', 'bulgur wheat|bulgur'),
    ('vegetable-bouillon-cubes', 'PRODUCT', 'vegetable stock cube'),
    ('curry-powders', 'PRODUCT', 'curry powder'),
    ('red-bell-peppers', 'CATEGORY', 'red pepper'),
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
        rows.append(price_ingredient({**raw, **({'key': match.get('key') or match.get('ingredientId') or match.get('id') or key} if key else {}),
                     'name': raw.get('name') or raw.get('foodName') or match.get('name') or key,
                     'canonicalName': match.get('canonicalName') or match.get('name') or raw.get('canonicalName') or raw.get('name') or raw.get('foodName')}))
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


async def _observations(bridge, *, barcode='', category='', category_type='CATEGORY', unit='', settings, refresh_since=None):
    """Coalesce repeated requests; bound concurrency and cache misses for an hour."""
    if not hasattr(bridge, '_price_queries'):
        bridge._price_queries = {}
        bridge._price_query_lock = asyncio.Lock()
        bridge._price_slots = asyncio.Semaphore(3)
    basis = next((candidate for candidate in ('g', 'ml', 'pcs') if unit and convert_amount(1, unit, candidate) is not None), unit)
    key = (barcode, category, category_type, settings['country'], settings['currency'], basis)
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
                        country=settings['country'], currency=settings['currency'], unit=unit))
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
                     and ref.get('country') == row['country'] and ref.get('currency') == row['currency']
                     and ref.get('basisUnit') == row['basisUnit']), None)
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
    reference = store.barcode_reference(barcode, country=country, currency=currency, unit=unit) if barcode else None
    kind = 'barcode'
    fallback = store.best_reference(identity, country=country, currency=currency, unit=unit) if identity else None
    if reference is None and barcode and fallback and fallback.get('barcode') == barcode:
        reference = fallback
    reason = 'no_observation'
    lookup_failed = False
    compatible_unit = not unit or any(convert_amount(1, unit, basis) is not None for basis in ('g', 'ml', 'pcs'))
    if (settings.get('autoGlobalPrices') or refresh_since is not None) and country and currency and compatible_unit:
        async def lookup(**kwargs):
            nonlocal reason, lookup_failed
            data = await _observations(bridge, settings=settings, refresh_since=refresh_since, unit=unit, **kwargs)
            if not data.get('ok'):
                reason = 'source_unavailable'
                lookup_failed = True
            elif data.get('searchLimited'):
                reason = 'search_limited'
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
                reference = store.barcode_reference(barcode, country=country, currency=currency, unit=unit)
        if reference is None and (refresh_since is not None or not _fresh(fallback)):
            category = category_for(ingredient)
            if category:
                row = await lookup(category=category[0], category_type=category[1])
                if row is None and not lookup_failed:
                    # Loose and packaged observations can exist for the same food.
                    other = 'PRODUCT' if category[1] == 'CATEGORY' else 'CATEGORY'
                    row = await lookup(category=category[0], category_type=other)
                if row:
                    await _store_observation(store, identity, row, generic=True)
                    fallback = store.best_reference(identity, country=country, currency=currency, unit=unit)
            elif not barcode and fallback is None:
                reason = 'category_unmapped'
    elif not compatible_unit:
        reason = 'basis_missing'
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
    identities = {}
    if not hasattr(bridge, '_price_hydrations'):
        bridge._price_hydrations = {}
    skipped = False
    for item in recipe.get('ingredients', []):
        identity = inventory_identity(item)
        weight = item.get('weight') if isinstance(item.get('weight'), dict) else {}
        amount = item.get('quantity') if item.get('quantity') is not None else weight.get('quantity')
        unit = item.get('unit') or weight.get('unit', '')
        if amount is None or not unit:
            lookup_status[identity] = 'recipe_amount_unknown'
            continue
        if (identity, unit) in seen:
            continue
        seen.add((identity, unit))
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
            async def hydrate(item=item, code=code, identity=identity, unit=unit, amount=amount):
                result = await product_price(bridge, barcode=code, ingredient=item,
                    quantity=amount, unit=unit, settings=settings,
                    refresh_since=refresh_since)
                # Stock barcodes and saved ingredient links are confirmed mappings.
                # Preserve a fresh generic estimate when the last package is gone.
                if result.get('reference') and result.get('matchKind') == 'barcode':
                    await _store_observation(store, identity, result['reference'])
                return result
            key = (identity, code, unit, settings['country'], settings['currency'])
            task = bridge._price_hydrations.get(key)
            if task is None or task.done():
                if len(bridge._price_hydrations) >= 500:
                    skipped = True
                    lookup_status[identity] = 'lookup_limit'
                    continue
                task = bridge.hass.async_create_background_task(hydrate(), 'Cook4Me ingredient price')
                bridge._price_hydrations[key] = task
                def cleanup(done, key=key):
                    if bridge._price_hydrations.get(key) is done:
                        bridge._price_hydrations.pop(key, None)
                    if not done.cancelled():
                        done.exception()  # Observe provider errors even after the caller leaves.
                task.add_done_callback(cleanup)
            tasks.append(task)
            identities[task] = identity
    # Returning a partial total must not cancel the work that fills its gaps.
    # Subsequent visible-recipe polls share these jobs, never force a new lookup.
    done, pending = await asyncio.wait(tasks, timeout=_RECIPE_WAIT_SECONDS) if tasks else (set(), set())
    failures = 0
    for task in done:
        if task.cancelled() or task.exception():
            failures += 1
            lookup_status[identities[task]] = 'source_unavailable'
        else:
            result = task.result()
            failures += bool(result.get('lookupFailed') or result.get('status') == 'source_unavailable')
            lookup_status[identities[task]] = result.get('status')
    for task in pending:
        lookup_status[identities[task]] = 'lookup_pending'
    cache = await recipe_cost_cache_for_bridge(bridge)
    cost = await cache.async_cost(recipe, inventory, store, country=settings['country'], currency=settings['currency'], force=refresh_since is not None)
    for row in cost.get('ingredients', []):
        if row.get('coverage', 0) < 1:
            row['priceStatus'] = ('recipe_amount_unknown' if row.get('reason') == 'recipe_amount_unknown'
                                  else lookup_status.get(row['identity']) or ('source_unavailable' if failures else 'no_observation'))
    cost.update(settings=settings, priceLookupIncomplete=bool(failures), priceLookupPending=bool(pending), priceSource='Open Prices',
                originalIngredients=True, ingredientLimitReached=skipped,
                checkedAt=datetime.now(timezone.utc).isoformat(), refreshed=refresh_since is not None,
                refreshPolicy={'observationsSeconds': 86400, 'missSeconds': 3600, 'failureSeconds': 60,
                               'onDemand': True, 'maximumObservationDays': 180})
    return cost
