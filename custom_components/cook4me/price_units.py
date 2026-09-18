"""Price-only normalization of explicit Cook4Me measurement identifiers.

Never guess grams per item, ingredient density, pinches or unspecified amounts.
The original recipe and cooker program are untouched.
"""
from __future__ import annotations

from copy import deepcopy

# Verified against unit labels in the bundled multilingual recipe catalog.
_UNITS = {'UNIT_27': 'g', 'UNIT_54': 'mg', 'UNIT_56': 'kg', 'UNIT_35': 'ml',
          'UNIT_14': 'cl', 'UNIT_22': 'dl', 'UNIT_32': 'l', 'UNIT_41': 'pcs'}
_EMBEDDED_SPOONS = {'tablespoon of olive oil', 'tablespoon of sesame oil',
                    'tablespoon of soy sauce', 'tablespoon of mirin',
                    'tablespoon of tomato purée', 'tablespoons of extra virgin olive oil',
                    'tablespoons mustard', 'tablespoons white vinegar',
                    'tablespoons of icing sugar', 'tablespoons of oil', 'tablespoons of lime juice'}
# Explicit labels only. Generic spoons, pinches, packs and cut slices remain
# unresolved; UNIT_18 ('spoon') and UNIT_36 ('piece/chunk') are not universal units.
_COUNT = {'piece', 'pieces', 'unit', 'units', 'unit(s)', 'stück', 'stueck',
          'darab', 'db', 'buc', 'buc.', 'adet', 'unità', 'unité', 'szt.', 'ks', 'komada'}
_SPOON_LABELS = {'el': 'UNIT_12', 'esslöffel': 'UNIT_12', 'càs': 'UNIT_12',
                 'c. à s.': 'UNIT_12', 'cuillère à soupe': 'UNIT_12',
                 'tl': 'UNIT_11', 'teelöffel': 'UNIT_11', 'càc': 'UNIT_11',
                 'c. à c.': 'UNIT_11', 'cuillère à café': 'UNIT_11'}


def price_ingredient(item):
    result = deepcopy(item)
    if not isinstance(result, dict):
        return result
    # Weight is a fallback only when the recipe has no explicit quantity.
    target = result
    if result.get('quantity') is None and isinstance(result.get('weight'), dict):
        target = result['weight']
    name = str(result.get('canonicalName') or result.get('name') or '').strip().casefold()
    if not target.get('unitKey') and not target.get('unit') and name in _EMBEDDED_SPOONS:
        target['unitKey'] = 'UNIT_12'
        target['unit'] = 'tbsp'
    key = target.get('unitKey')
    if key in _UNITS:
        target['unit'] = _UNITS[key]
    elif not key or key in {'UNIT_18', 'UNIT_36'}:
        label = str(target.get('unit') or '').strip().casefold()
        if label in _COUNT:
            target['unit'] = 'pcs'
        elif label in _SPOON_LABELS:
            target['unitKey'] = _SPOON_LABELS[label]
            target['unit'] = 'tbsp' if target['unitKey'] == 'UNIT_12' else 'tsp'
    return result
