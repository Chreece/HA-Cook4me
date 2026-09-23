"""Price-only normalization of explicit Cook4Me measurement identifiers.

Never guess grams per item, ingredient density, pinches or unspecified amounts.
The original recipe and cooker program are untouched.
"""
from __future__ import annotations

from copy import deepcopy
import unicodedata

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
          'darab', 'db', 'buc', 'buc.', 'adet', 'unità', 'unité', 'szt.', 'ks', 'komada',
          'τεμ', 'τεμ.', 'τεμάχιο', 'τεμάχια'}
_SPOON_LABELS = {'el': 'UNIT_12', 'esslöffel': 'UNIT_12', 'càs': 'UNIT_12',
                 'c. à s.': 'UNIT_12', 'cuillère à soupe': 'UNIT_12',
                 'tl': 'UNIT_11', 'teelöffel': 'UNIT_11', 'càc': 'UNIT_11',
                 'c. à c.': 'UNIT_11', 'cuillère à café': 'UNIT_11',
                 'κ.σ.': 'UNIT_12', 'κ. σ.': 'UNIT_12',
                 'κουταλιά της σούπας': 'UNIT_12', 'κουταλιές της σούπας': 'UNIT_12',
                 'κ.γ.': 'UNIT_11', 'κ. γ.': 'UNIT_11',
                 'κουταλάκι του γλυκού': 'UNIT_11', 'κουταλάκια του γλυκού': 'UNIT_11'}
# Explicit Greek metric labels only; never treat a chunk, packet or generic
# spoon as a known mass, count or volume. This is a price-only copy of the row.
_METRIC_LABELS = {'γρ': 'g', 'γρ.': 'g', 'γραμμάριο': 'g', 'γραμμάρια': 'g',
                  'κιλό': 'kg', 'κιλά': 'kg', 'χιλιόγραμμο': 'kg', 'χιλιόγραμμα': 'kg',
                  'χιλιοστόλιτρο': 'ml', 'χιλιοστόλιτρα': 'ml',
                  'λίτρο': 'l', 'λίτρα': 'l'}


def _unit_label(value):
    return ' '.join(unicodedata.normalize('NFC', str(value or '').casefold()).split())


# Greek final sigma and decomposed accents must normalize on both sides.
_COUNT = {_unit_label(label) for label in _COUNT}
_SPOON_LABELS = {_unit_label(label): key for label, key in _SPOON_LABELS.items()}
_METRIC_LABELS = {_unit_label(label): unit for label, unit in _METRIC_LABELS.items()}


def price_ingredient(item):
    result = deepcopy(item)
    if not isinstance(result, dict):
        return result
    # Weight is a fallback only when the recipe has no explicit quantity.
    target = result
    if result.get('quantity') is None and isinstance(result.get('weight'), dict):
        target = result['weight']
    # Use the same decimal-comma convention as the existing cost parser.
    # Invalid numbers remain invalid; quantity validation belongs to the caller.
    quantity = target.get('quantity')
    if isinstance(quantity, str) and ',' in quantity:
        try:
            target['quantity'] = float(quantity.replace(',', '.'))
        except ValueError:
            pass
    name = str(result.get('canonicalName') or result.get('name') or '').strip().casefold()
    if not target.get('unitKey') and not target.get('unit') and name in _EMBEDDED_SPOONS:
        target['unitKey'] = 'UNIT_12'
        target['unit'] = 'tbsp'
    key = target.get('unitKey')
    if key in _UNITS:
        target['unit'] = _UNITS[key]
    elif not key or key in {'UNIT_18', 'UNIT_36'}:
        label = _unit_label(target.get('unit'))
        if label in _METRIC_LABELS:
            target['unit'] = _METRIC_LABELS[label]
        elif label in _COUNT:
            target['unit'] = 'pcs'
        elif label in _SPOON_LABELS:
            target['unitKey'] = _SPOON_LABELS[label]
            target['unit'] = 'tbsp' if target['unitKey'] == 'UNIT_12' else 'tsp'
    return result
