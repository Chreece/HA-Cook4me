"""Reviewed, disclosed quantity estimates for recipe costs only.

Native stock/purchase units always win. Never change cooking or nutrition data,
fill unspecified amounts, infer cups, or equate a pack/bunch with one ingredient.
"""
from functools import lru_cache
import json
import math
from pathlib import Path

from .price_units import price_ingredient
from .inventory import convert_amount
from .price_identity import pricing_name

_NIST = 'https://www.nist.gov/pml/owm/metric-si/metric-kitchen/metric-kitchen-cooking-measurement-equivalencies'
_SPOONS = {'UNIT_11': 'tsp', 'UNIT_12': 'tbsp', 'tsp': 'tsp', 'teaspoon': 'tsp',
           'teaspoons': 'tsp', 'tbsp': 'tbsp', 'tablespoon': 'tbsp', 'tablespoons': 'tbsp'}
_COUNTS = {'egg', 'eggs', 'onion', 'onions', 'carrot', 'carrots', 'tomato', 'tomatoes',
           'cherry tomato', 'cherry tomatoes', 'apple', 'apples', 'zucchini', 'courgette',
           'courgettes', 'aubergine', 'aubergines', 'eggplant', 'red pepper', 'red bell pepper',
           'cucumber', 'cucumbers', 'leek', 'leeks', 'white potatoes', 'potato', 'potatoes',
           'lemon', 'lemons', 'lime', 'limes', 'orange', 'oranges', 'shallot', 'shallots',
           'welsh onion', 'spring onion', 'spring onions', 'green onion', 'green onions'}


@lru_cache(maxsize=1)
def _portions():
    payload = json.loads((Path(__file__).with_name('catalog') / 'price_portions.v1.json').read_text())
    return {(name, row['measure']): row for row in payload['portions'] for name in row['names']}


@lru_cache(maxsize=1)
def _densities():
    payload = json.loads((Path(__file__).with_name('catalog') / 'price_densities.v1.json').read_text())
    return {name: row for row in payload['densities'] for name in row['names']}


def price_options(raw):
    """Return native amount first, followed by explicitly labelled alternatives."""
    item = price_ingredient(raw)
    weight = item.get('weight') if isinstance(item.get('weight'), dict) else {}
    target = item if item.get('quantity') is not None else weight
    try:
        amount = float(target.get('quantity'))
    except (ValueError, TypeError):
        return []
    if isinstance(target.get('quantity'), bool) or not math.isfinite(amount) or amount <= 0:
        return []
    unit = str(target.get('unit') or '').strip()
    key = str(target.get('unitKey') or '')
    name = pricing_name(item)
    options = [{'quantity': amount, 'unit': unit}] if unit else []
    if key in {'UNIT_138', 'UNIT_50'}:
        unit = 'pcs'
        options = [{'quantity': amount, 'unit': unit}]
    if not unit and not key and name in _COUNTS and amount <= 20:
        unit = 'pcs'
        options.append({'quantity': amount, 'unit': unit, 'estimate': {
            'kind': 'implicit_count', 'label': 'Unlabelled whole ingredient treated as a count',
            'sourceQuantity': amount, 'sourceUnit': '', 'quantity': amount, 'unit': unit}})
    measure = _SPOONS.get(key) or _SPOONS.get(unit.casefold())
    if key == 'UNIT_28' or unit.casefold() in {'clove', 'cloves'}:
        measure = 'clove'
    elif unit == 'pcs':
        measure = 'piece'
    if measure in {'tsp', 'tbsp'}:
        ml = 5 if measure == 'tsp' else 15
        # A tablespoon has different conventions; this is a disclosed cooking estimate.
        options.append({'quantity': amount * ml, 'unit': 'ml', 'estimate': {
            'kind': 'spoon_volume', 'label': f'1 {measure} ≈ {ml} ml', 'sourceUrl': _NIST,
            'sourceQuantity': amount, 'sourceUnit': measure, 'quantity': amount * ml, 'unit': 'ml'}})
    if name in {'vegetable stock', 'vegetable stock cube'} and key in {'UNIT_17', 'UNIT_21'}:
        options.append({'quantity': amount, 'unit': 'pcs', 'estimate': {
            'kind': 'stock_cube', 'label': 'Stock cube count; named package uses 11 g cubes',
            'sourceUrl': 'https://www.dm.de/p/d/1490263/dmbio-gemuesebruehwuerfel',
            'sourceQuantity': amount, 'sourceUnit': unit, 'quantity': amount, 'unit': 'pcs'}})
    portion = _portions().get((name, measure))
    factor = 1
    if portion is None and measure in {'tsp', 'tbsp'}:
        portion = _portions().get((name, 'tbsp' if measure == 'tsp' else 'tsp'))
        factor = 1 / 3 if measure == 'tsp' else 3
    if portion:
        grams = amount * portion['grams'] * factor
        options.append({'quantity': grams, 'unit': 'g', 'estimate': {
            'kind': 'food_portion', 'label': f"USDA {portion['food']}: {portion['portion']}",
            'sourceUrl': f"https://fdc.nal.usda.gov/food-details/{portion['fdcId']}/nutrients",
            'fdcId': portion['fdcId'], 'portionId': portion['portionId'],
            'sourceQuantity': amount, 'sourceUnit': measure, 'quantity': grams, 'unit': 'g',
            'assumedCount': not bool(target.get('unit') or key)}})
    # A sourced portion also lets a gram recipe use a per-piece price, and a
    # measured spoon lets mass and volume meet without a universal water density.
    grams = convert_amount(amount, unit, 'g')
    millilitres = convert_amount(amount, unit, 'ml')
    density = _densities().get(name)
    if density and (grams is not None or millilitres is not None or measure in {'tsp', 'tbsp'}):
        volume = millilitres if millilitres is not None else amount * (5 if measure == 'tsp' else 15)
        converted = grams / density['gramsPerMl'] if grams is not None else volume * density['gramsPerMl']
        destination = 'ml' if grams is not None else 'g'
        options.append({'quantity': converted, 'unit': destination, 'estimate': {
            'kind': 'food_density', 'label': density['label'], 'sourceUrl': density['sourceUrl'],
            'sourceQuantity': amount, 'sourceUnit': unit, 'quantity': converted, 'unit': destination}})
    piece = _portions().get((name, 'piece'))
    spoon = _portions().get((name, 'tbsp')) or _portions().get((name, 'tsp'))
    if grams is not None and piece:
        options.append({'quantity': grams / piece['grams'], 'unit': 'pcs', 'estimate': {
            'kind': 'food_portion', 'label': f"USDA {piece['food']}: {piece['portion']}",
            'sourceUrl': f"https://fdc.nal.usda.gov/food-details/{piece['fdcId']}/nutrients",
            'fdcId': piece['fdcId'], 'portionId': piece['portionId'],
            'sourceQuantity': amount, 'sourceUnit': unit, 'quantity': grams / piece['grams'], 'unit': 'pcs'}})
    if spoon and (grams is not None or millilitres is not None):
        volume = 15 if spoon['measure'] == 'tbsp' else 5
        converted = grams / spoon['grams'] * volume if grams is not None else millilitres / volume * spoon['grams']
        destination = 'ml' if grams is not None else 'g'
        options.append({'quantity': converted, 'unit': destination, 'estimate': {
            'kind': 'food_density', 'label': f"USDA {spoon['food']}: {spoon['portion']}; approximate spoon volume",
            'sourceUrl': f"https://fdc.nal.usda.gov/food-details/{spoon['fdcId']}/nutrients",
            'volumeSourceUrl': _NIST, 'fdcId': spoon['fdcId'], 'portionId': spoon['portionId'],
            'sourceQuantity': amount, 'sourceUnit': unit, 'quantity': converted, 'unit': destination}})
    return options
