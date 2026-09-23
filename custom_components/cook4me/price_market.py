"""Explicit supermarket-language requests and country-scoped price evidence.

Open Prices is a barcode/category API, not a translated free-text search API.
Keep its identifiers untouched. Carry a separate, catalog-derived local name
through the lookup boundary; never send a UI/shopping composite as a search term.
All catalog access in this module must be called through HA's executor.
"""
from __future__ import annotations

from copy import copy, deepcopy
from datetime import datetime, timedelta, timezone

from . import release_catalog
from .costs import _country, _currency, _number
from .inventory import inventory_identity
from .shopping_presentation import normalize_supermarket_language


def normalize_price_market(settings):
    """Language never selects a country or converts a currency."""
    result = dict(settings or {})
    result['country'] = _country(result.get('country'))
    result['currency'] = _currency(result.get('currency'))
    result['supermarketLanguage'] = normalize_supermarket_language(
        result.get('supermarketLanguage'), country=result['country'], fallback='en'
    )
    return result


def market_ready(settings):
    return bool(settings.get('country') and settings.get('currency'))


def price_lookup_ingredient(ingredient, settings):
    """Return a local-language price request without mutating recipe/inventory.

    An unkeyed ingredient retains its original inventory identity: translating
    its name must not create a different saved-price key. Category matching uses
    canonicalName, not the localized label.
    """
    settings = normalize_price_market(settings)
    raw = deepcopy(ingredient) if isinstance(ingredient, dict) else {'name': str(ingredient or '')}
    key = raw.get('key') or raw.get('foodKey') or raw.get('ingredientId')
    if key:
        raw['key'] = str(key)
    identity = inventory_identity(raw)
    label = release_catalog.ingredient_price_label(raw, settings['supermarketLanguage'])
    result = dict(raw)
    result['name'] = label['name']
    result['canonicalName'] = label['canonicalName']
    result['priceLookupIdentity'] = identity
    result['priceLookup'] = {
        'identity': identity,
        'ingredientName': label['name'],
        'ingredientLanguage': label['language'],
        'supermarketLanguage': settings['supermarketLanguage'],
        'translationMissing': not label['translationAvailable'],
        # Only a proven local label is eligible for a name-based provider.
        'queryName': label['name'] if label['translationAvailable'] else '',
        'country': settings['country'],
        'currency': settings['currency'],
        'providerLookup': 'barcode_or_category',
        'nameSource': label['source'],
    }
    return result


def local_observation_result(data, settings, ingredient=None):
    """Reject foreign, undated, expired, future or unusable observations.

    This final boundary applies equally to offline snapshots and live results.
    Exact paid purchases are not observations and are handled separately.
    """
    settings = normalize_price_market(settings)
    result = deepcopy(data) if isinstance(data, dict) else {'ok': False, 'reason': 'invalid_response'}
    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=180)
    rows = []
    items = result.get('items')
    if items is not None and not isinstance(items, (list, tuple)):
        result.update(ok=False, reason='invalid_response')
        items = []
    if market_ready(settings):
        for row in items or []:
            if not isinstance(row, dict) or not row.get('usable'):
                continue
            if _country(row.get('country')) != settings['country'] or _currency(row.get('currency')) != settings['currency']:
                continue
            amount, basis = _number(row.get('amount')), _number(row.get('basisQuantity'))
            if amount is None or basis is None or basis <= 0 or not row.get('basisUnit'):
                continue
            try:
                observed = datetime.strptime(str(row.get('date') or ''), '%Y-%m-%d').date()
            except (TypeError, ValueError):
                continue
            if cutoff <= observed <= today:
                rows.append({**row, 'country': settings['country'], 'currency': settings['currency']})
    else:
        result.update(ok=False, reason='choose_country')
    result['items'] = rows
    result['usableCount'] = len(rows)
    result['lookupMarket'] = {field: settings[field] for field in ('country', 'currency', 'supermarketLanguage')}
    # Attach caller-specific labels AFTER reading a shared evidence cache.
    # Two ingredients can share a category without sharing their display names.
    if isinstance(ingredient, dict) and isinstance(ingredient.get('priceLookup'), dict):
        result['lookupIngredient'] = deepcopy(ingredient['priceLookup'])
    return result


async def market_observations(bridge, *, fetch, ingredient, settings, **kwargs):
    """Pass the local ingredient context to the provider adapter boundary."""
    settings = normalize_price_market(settings)
    if not market_ready(settings):
        return local_observation_result({'items': []}, settings, ingredient)
    # The adapter translates a local ingredient identity into the provider's
    # barcode/category parameters. Do not invent unsupported search_terms/lc
    # parameters for the Open Prices /prices endpoint.
    data = await fetch(bridge, settings=settings, **kwargs)
    return local_observation_result(data, settings, ingredient)


def local_cost_store(saved, settings):
    """Read-only market view; preserve exact paid lots in their paid currency."""
    settings = normalize_price_market(settings)
    store = copy(saved)
    data = deepcopy(saved._data)
    data['settings'] = {**data.get('settings', {}), **settings}
    refs = {}
    for key, row in (data.get('references') or {}).items():
        if not isinstance(row, dict):
            continue
        paid_lot = (str(row.get('identity') or '').startswith('lot:')
                    and (row.get('source') in {'purchase', 'manual'}
                         or row.get('confidence') in {'exact_purchase', 'user_entered'}))
        local = (market_ready(settings)
                 and _country(row.get('country')) == settings['country']
                 and _currency(row.get('currency')) == settings['currency'])
        if paid_lot or local:
            refs[key] = row
    data['references'] = refs
    store._data = data
    return store


def annotate_market_cost(cost, recipe, settings):
    """Rebind local labels per response, outside the numeric price cache."""
    settings = normalize_price_market(settings)
    result = deepcopy(cost)
    by_identity = {}
    for raw in recipe.get('ingredients') or []:
        item = price_lookup_ingredient(raw, settings)
        by_identity.setdefault(item['priceLookupIdentity'], item)
    for row in result.get('ingredients') or []:
        item = by_identity.get(row.get('identity')) if isinstance(row, dict) else None
        if item is not None:
            row['supermarketName'] = item['name']
            row['supermarketLanguage'] = settings['supermarketLanguage']
            row['priceLookup'] = deepcopy(item['priceLookup'])
    result['lookupMarket'] = {field: settings[field] for field in ('country', 'currency', 'supermarketLanguage')}
    return result
