"""Explicit planning allowances for unmeasured basics, never price evidence.

Names are reviewed exact canonical forms. No substring matching: salted butter,
bell peppers, oil and stock still need quantities and compatible prices.
"""
from .price_identity import pricing_name


BASIC_NAMES = frozenset('''salt
salt and pepper
ground black pepper
black pepper
salt and black pepper
sea salt
white pepper
pepper and salt
salt & pepper
white pepper and salt
salt, freshly ground pepper
fine salt
coarse salt
coarsely ground black pepper
tap water
water
boiling water
hot water
black pepper (a little)
a- black pepper, a little
pepper salt (a little)
black pepper (for seasoning)
pepper (a little)
black pepper, a little
salt and pepper (for meat), a little
black pepper (for finishing)
cold water for soaking the gelatin
water, enough to cover the ingredients
salt and pepper for seasoning
salt and pepper, to taste
salt and pepper (to taste)
salt and black pepper, if needed
salt and black pepper (to taste)
salt and pepper to taste
pepper and salt to taste
water (enough to cover)
salt and pepper, to season
salt and pepper, for seasoning
salt and freshly ground pepper to taste
salt and pepper to taste (depending on the seasoning of the stock)
water (preferably filtered)
salt (fleur de sel recommended)
water (for slurry)
salt (a little)
coarsely ground black pepper (a little)
pepper (for finishing)
coarsely ground black pepper, a little for sauce
coarsely ground black pepper (for finishing)
pepper, a little
water (for gelatin)
salt (for finishing)
water (for sauce)
salt and pepper (for finishing)
water (for mixing)
pepper (for finishing), a little
salt and pepper, a little
salt and pepper (for sauce)
a- salt and pepper, as needed
water (for goji berries)
water (for blooming gelatin)
coarse salt (for finishing), a little
coarsely ground pepper (for finishing), a little
water (for soaking/blooming)
salt, a little for sauce
b- water (for gelatin)
c- hot water
water (for steaming basket)
salt (for marinating)
pepper, a little for marinating
boiling water, as needed for pouring over mackerel
white pepper (for garnish), as needed
salt, a little (for pre-seasoning)
salt and pepper, as needed
c- pepper salt, a little
pepper salt (for sauce)
water (for dissolving gelatin)
b- coarsely ground black pepper, a little
salt (for sauce), a little
coarsely ground pepper, a little
coarsely ground black pepper (for finishing), a little
a- pepper salt
pepper (for seasoning), a little
coarse pepper salt (for seasoning), a little
pepper salt (for seasoning), a little
coarsely ground salt and pepper, a little for finishing
water (for potato-starch slurry)
pepper (seasoning)'''.splitlines())


def zero_cost_allowance(item, currency):
    if not isinstance(item, dict) or item.get('priceCatalogExcluded') or not currency:
        return None
    # An invalid value or a known number with an unknown unit is not absence.
    weight = item.get('weight') if isinstance(item.get('weight'), dict) else {}
    if any(value is not None and value != '' for value in (item.get('quantity'), weight.get('quantity'))):
        return None
    name = pricing_name(item)
    # Provider "Pepper" can mean a vegetable. Only a seasoning unit or an
    # ad-hoc, unkeyed ingredient disambiguates this otherwise ambiguous name.
    identity = any(item.get(key) for key in ('key', 'ingredientId', 'foodKey', 'id'))
    seasoning_pepper = name == 'pepper' and (not identity or item.get('unitKey') in {'UNIT_42', 'UNIT_44'})
    if name not in BASIC_NAMES and not seasoning_pepper:
        return None
    return {'kind': 'unmeasured_basic_zero', 'policy': 'unmeasured-basics-v99',
            'canonicalName': name, 'amount': 0.0, 'currency': currency,
            'confidence': 'assumption', 'quantityInferred': False}


def price_confidence(cost):
    """Evidence level, independent of how cheap or expensive the recipe is."""
    totals = cost.get('budgetTotalsByCurrency') or cost.get('totalsByCurrency') or {}
    if not totals:
        return 'unavailable'
    if not (cost.get('budgetComplete') or cost.get('complete')):
        return 'partial'
    if cost.get('zeroCostIngredientCount') or cost.get('fallbackIngredientCount'):
        return 'assumed'
    if all(not row.get('quantityEstimate') and row.get('sourceKinds') and
           set(row['sourceKinds']) <= {'exact_purchase', 'manual_reference'}
           for row in cost.get('ingredients', [])):
        return 'personal'
    return 'reference'
