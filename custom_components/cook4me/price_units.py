"""Price-only normalization of explicit Cook4Me measurement identifiers.

Never guess grams per item, ingredient density, pinches or unspecified amounts.
The original recipe and cooker program are untouched.
"""
from __future__ import annotations

from copy import deepcopy

# Verified against unit labels in the bundled multilingual recipe catalog.
_UNITS = {'UNIT_27': 'g', 'UNIT_54': 'mg', 'UNIT_56': 'kg', 'UNIT_35': 'ml',
          'UNIT_14': 'cl', 'UNIT_22': 'dl', 'UNIT_32': 'l', 'UNIT_41': 'pcs'}
_COUNT = {'piece', 'pieces', 'unit', 'units', 'unit(s)'}


def price_ingredient(item):
    result = deepcopy(item)
    if not isinstance(result, dict):
        return result
    # Weight is a fallback only when the recipe has no explicit quantity.
    target = result
    if result.get('quantity') is None and isinstance(result.get('weight'), dict):
        target = result['weight']
    key = target.get('unitKey')
    if key in _UNITS:
        target['unit'] = _UNITS[key]
    elif str(target.get('unit') or '').strip().casefold() in _COUNT:
        target['unit'] = 'pcs'
    return result
