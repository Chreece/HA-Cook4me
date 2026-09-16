"""Data-derived budget fallbacks, separate from ingredient-price evidence.

A comparable-food median is a planning assumption, never an observed price of
this ingredient. If no peer group has a compatible unit, use the broader local
food basket and label it explicitly. Never convert currency or invent amounts.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from collections import defaultdict, deque
from functools import lru_cache
import json
import math
from pathlib import Path
from statistics import median

from .inventory import convert_amount
from .price_identity import pricing_name
from .price_measurements import price_options
from .price_snapshot import _load, category_observation_allowed


@lru_cache(maxsize=1)
def _groups():
    data = json.loads((Path(__file__).with_name('catalog') / 'price_benchmarks.v1.json').read_text())
    if data.get('schemaVersion') != 1:
        raise ValueError('Unsupported budget benchmark schema')
    return data['groups']


def _group(item):
    name = pricing_name(item)
    category = item.get('priceCategory')
    return next((g for g in _groups() if category in g['categories'] or name in g['names']), None)


@lru_cache(maxsize=32)
def _pools(country, currency, today):
    cutoff = today - timedelta(days=180)
    group_tags = {tag: g['id'] for g in _groups() for tag in g['categories']}
    latest = {}
    for row in _load().get('observations', []):
        if row.get('country') != country or row.get('currency') != currency or not row.get('usable'):
            continue
        if row.get('source') == 'utility_snapshot' or row.get('categoryExclusions'):
            continue
        groups = {group_tags[tag] for tag in row.get('categories', [])
                  if tag in group_tags and category_observation_allowed(row, tag)}
        if not groups:
            continue
        try:
            observed = date.fromisoformat(row['date'])
            if isinstance(row['amount'], bool) or isinstance(row['basisQuantity'], bool):
                continue
            amount, quantity = float(row['amount']), float(row['basisQuantity'])
            if not cutoff <= observed <= today or not math.isfinite(amount) or not math.isfinite(quantity) or amount <= 0 or quantity <= 0:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        unit = next((u for u in ('g', 'ml', 'pcs') if convert_amount(1, row.get('basisUnit'), u) is not None), None)
        if not unit:
            continue
        basis = convert_amount(quantity, row['basisUnit'], unit)
        if not basis or not math.isfinite(amount / basis):
            continue
        identity = (str(row.get('barcode') or row.get('productName') or row.get('product_name') or row.get('id')), unit)
        if identity in latest and latest[identity]['date'] >= row['date']:
            continue
        latest[identity] = {'id': row['id'], 'date': row['date'], 'unit': unit, 'rate': amount / basis,
            'groups': groups, 'name': row.get('productName') or row.get('product_name') or str(row['id']),
            'sourceUrl': row.get('sourceUrl') or ('https://prices.openfoodfacts.org/prices/' + str(row['id']) if str(row['id']).isdigit() else '')}
    pools = {}
    for row in latest.values():
        for group in row['groups'] | {'basket'}:
            pools.setdefault((group, row['unit']), []).append(row)
    return pools


def fallback_estimate(item, *, country, currency, fraction=1.0):
    if not item.get('priceCatalogMatched') or not country or not currency or pricing_name(item) in {'water', 'tap water'}:
        return None
    if not math.isfinite(fraction) or fraction <= 0:
        return None
    pools = _pools(country, currency, datetime.now(timezone.utc).date())
    group = _group(item)
    options = price_options(item)
    # Prefer a sourced edible mass over unlike per-piece produce comparisons.
    candidates = []
    for option in options:
        for index, unit in enumerate(('g', 'ml', 'pcs')):
            amount = convert_amount(option['quantity'], option['unit'], unit)
            if amount is None or amount <= 0:
                continue
            peers = pools.get((group['id'], unit), []) if group else []
            level = 'food_group' if peers else 'food_basket'
            peers = peers or pools.get(('basket', unit), [])
            if peers:
                candidates.append((level != 'food_group', index, amount, unit, option, peers, level))
    if not candidates:
        return None
    _, _, amount, unit, option, peers, level = min(candidates, key=lambda c: c[:2])
    amount *= min(1.0, fraction)
    peers = sorted(peers, key=lambda row: row['rate'])
    rates = [row['rate'] for row in peers]
    selected = sorted({0, (len(peers)-1)//2, len(peers)//2, len(peers)-1})
    return {'kind': 'budget_benchmark', 'level': level, 'confidence': 'low',
        'group': group['id'] if level == 'food_group' else 'basket',
        'groupLabel': group['label'] if level == 'food_group' else 'Local food basket',
        'country': country, 'currency': currency, 'quantity': amount, 'unit': unit,
        'amount': round(amount * median(rates), 4), 'low': round(amount * min(rates), 4),
        'high': round(amount * max(rates), 4), 'unitPrice': median(rates),
        'sampleCount': len(peers), 'method': 'median', 'rangeKind': 'observed_peer_spread',
        'oldestDate': min(row['date'] for row in peers), 'newestDate': max(row['date'] for row in peers),
        'quantityEstimate': deepcopy(option.get('estimate')),
        'sourceIds': [row['id'] for row in peers],
        'sources': [{k: peers[i][k] for k in ('id', 'name', 'sourceUrl', 'date', 'rate', 'unit')} for i in selected]}


def add_budget_estimates(cost, recipe, store, *, country, currency):
    """Keep known totals/coverage intact; add a separate estimated budget."""
    if not store.settings.get('autoGlobalPrices', True):
        return cost
    from .inventory import inventory_identity
    ingredients = defaultdict(deque)
    for item in recipe.get('ingredients', []):
        if isinstance(item, dict):
            ingredients[inventory_identity(item)].append(item)
    totals = dict(cost.get('totalsByCurrency') or {})
    low, high = dict(totals), dict(totals)
    count = 0
    for row in cost.get('ingredients', []):
        matches = ingredients.get(row.get('identity'))
        item = matches.popleft() if matches else None
        coverage = row.get('coverage', 0)
        if coverage >= 1:
            continue
        # Do not infer an amount for a row rejected by the actual calculator.
        if not item or row.get('reason') == 'recipe_amount_unknown':
            continue
        estimate = fallback_estimate(item, country=country, currency=currency, fraction=1-coverage)
        if estimate is None:
            continue
        row['fallbackEstimate'] = estimate
        row['budgetCoverage'] = 1.0
        count += 1
        for target, field in ((totals, 'amount'), (low, 'low'), (high, 'high')):
            target[currency] = target.get(currency, 0) + estimate[field]
    if not count:
        return cost
    rows = cost['ingredients']
    covered = sum(row.get('coverage') == 1 or row.get('budgetCoverage') == 1 for row in rows)
    servings = cost.get('servings')
    cost.update(budgetEstimated=True, fallbackIngredientCount=count, budgetTotalsByCurrency={k: round(v, 2) for k,v in totals.items()},
        budgetRangeByCurrency={k: {'low': round(low[k], 2), 'high': round(high[k], 2)} for k in totals},
        budgetPerServingByCurrency={k: round(v/servings, 2) for k,v in totals.items()} if servings and servings > 0 else {},
        budgetIngredientCount=covered, budgetComplete=bool(rows) and covered == len(rows),
        budgetMissingIngredientCount=len(rows)-covered, budgetMethod='local-food-benchmark-v91')
    return cost
