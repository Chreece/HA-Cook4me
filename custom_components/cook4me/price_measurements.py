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
           'welsh onion', 'spring onion', 'spring onions', 'green onion', 'green onions',
           'raw beetroot', 'parsnip', 'parsnips', 'banana', 'bananas', 'pear', 'pears', 'plum', 'plums', 'strawberry', 'strawberries',
           'radish', 'radishes', 'date', 'dates', 'dried dates', 'pitted dates', 'medjool date', 'medjool dates', 'small pumpkin', 'small hokkaido pumpkin',
           'asparagus', 'green asparagus', 'fennel', 'turnip', 'green pepper', 'green bell pepper',
           'swede', 'rutabaga', 'shiitake mushroom', 'shiitake mushrooms',
           'fresh shiitake mushroom', 'fresh shiitake mushrooms'}

_GELATINE_SHEETS = {'leaf gelatine', 'gelatine sheet', 'gelatine sheets', 'gelatin sheet', 'gelatin sheets'}
_VANILLA_PODS = {'vanilla pod', 'vanilla pods'}


@lru_cache(maxsize=1)
def _portions():
    payload = json.loads((Path(__file__).with_name('catalog') / 'price_portions.v1.json').read_text())
    rows = payload['portions']
    products = json.loads((Path(__file__).with_name('catalog') / 'price_reference_portions.v1.json').read_text())
    return {(name, row['measure']): row for row in rows + products['portions'] for name in row['names']}


@lru_cache(maxsize=1)
def _densities():
    payload = json.loads((Path(__file__).with_name('catalog') / 'price_densities.v1.json').read_text())
    return {name: row for row in payload['densities'] for name in row['names']}


def _portion_evidence(row):
    if row.get('fdcId'):
        return {'kind': 'food_portion', 'label': f"USDA {row['food']}: {row['portion']}",
                'sourceUrl': f"https://fdc.nal.usda.gov/food-details/{row['fdcId']}/nutrients",
                'fdcId': row['fdcId'], 'portionId': row['portionId']}
    return {'kind': 'reference_portion', 'label': row['label'], 'sourceUrl': row['sourceUrl']}


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
    # The food identity establishes what is being counted. UNIT_28 is also
    # labelled "gousse"/"clove" for vanilla pods in translated provider data.
    # This changes pricing only; never interpret a packet, seed or gram as a pod.
    implicit = not unit and not key and amount <= 20
    sheet = name in _GELATINE_SHEETS and (implicit or unit == 'pcs' or key in {'UNIT_24', 'UNIT_98', 'UNIT_50', 'UNIT_138'}
        or (not key and unit.casefold() in {'leaf', 'leaves', 'sheet', 'sheets'}))
    pod = name in _VANILLA_PODS and (implicit or unit == 'pcs' or key in {'UNIT_28', 'UNIT_50', 'UNIT_138'}
        or (not key and unit.casefold() in {'pod', 'pods'}))
    if sheet or pod:
        count_unit = 'sheet' if sheet else 'pod'
        estimate = {'kind': 'ingredient_count', 'label': f'{name}: count of individual {count_unit}s; no package-size or weight assumption',
            'sourceQuantity': amount, 'sourceUnit': '' if implicit else count_unit,
            'quantity': amount, 'unit': 'pcs', 'assumedCount': implicit}
        # Use one count option, retaining its explanation even for native pcs.
        options = [option for option in options if option['unit'] != 'pcs']
        options.append({'quantity': amount, 'unit': 'pcs', 'estimate': estimate})
        unit = 'pcs'
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
    # Only food-specific published portions can convert a leaf or sprig. A
    # bunch/packet remains unresolved; these unit IDs never imply a pack size.
    elif key == 'UNIT_24' or unit.casefold() in {'leaf', 'leaves'}:
        measure = 'leaf'
    elif key == 'UNIT_10' or unit.casefold() in {'sprig', 'sprigs'}:
        measure = 'sprig'
    # These stock names are used for both liquid and concentrated products in
    # provider translations. A spoonful does not establish the prepared form.
    prepared_stock = name in {'chicken stock', 'beef stock', 'veal stock'}
    if measure in {'tsp', 'tbsp'} and not prepared_stock:
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
            **_portion_evidence(portion),
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
    # A sourced spoon mass can also use a sourced whole-food yield (e.g. fresh
    # coconut). Keep both portion facts in the estimate; never infer a pack size.
    if grams is None and portion and piece and measure in {'tsp', 'tbsp'}:
        count = amount * portion['grams'] * factor / piece['grams']
        options.append({'quantity': count, 'unit': 'pcs', 'estimate': {
            **_portion_evidence(piece),
            'label': _portion_evidence(portion)['label'] + '; ' + _portion_evidence(piece)['label'],
            'portionIds': [portion.get('portionId'), piece.get('portionId')],
            'sourceQuantity': amount, 'sourceUnit': measure, 'quantity': count, 'unit': 'pcs'}})
    if grams is not None and piece:
        options.append({'quantity': grams / piece['grams'], 'unit': 'pcs', 'estimate': {
            **_portion_evidence(piece),
            'sourceQuantity': amount, 'sourceUnit': unit, 'quantity': grams / piece['grams'], 'unit': 'pcs'}})
    if spoon and (grams is not None or millilitres is not None):
        volume = 15 if spoon['measure'] == 'tbsp' else 5
        converted = grams / spoon['grams'] * volume if grams is not None else millilitres / volume * spoon['grams']
        destination = 'ml' if grams is not None else 'g'
        options.append({'quantity': converted, 'unit': destination, 'estimate': {
            **_portion_evidence(spoon), 'kind': 'food_density',
            'label': _portion_evidence(spoon)['label'] + '; approximate spoon volume',
            'volumeSourceUrl': _NIST,
            'sourceQuantity': amount, 'sourceUnit': unit, 'quantity': converted, 'unit': destination}})
    recovered = item.get('priceQuantityEvidence')
    if recovered:
        for option in options:
            if option.get('estimate'):
                option['estimate'] = {**option['estimate'], 'recipeSource': recovered}
            else:
                option['estimate'] = {**recovered, 'quantity': option['quantity'], 'unit': option['unit']}
    return options
