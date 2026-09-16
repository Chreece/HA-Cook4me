"""Reviewed provider identities used only for costing, never cooking data."""

# The provider's English name "Pepper" covers three different foods. Only the
# confirmed Pfeffer/Poivre identity may use ground black pepper references.
_NAMES = {'M_FOOD_388': 'ground black pepper', 'M_FOOD_131': 'tomato paste'}


def pricing_name(item):
    key = str(item.get('key') or item.get('ingredientId') or item.get('foodKey') or item.get('id') or '')
    return _NAMES.get(key, str(item.get('canonicalName') or item.get('name') or '').strip().casefold())


def is_cost_heading(item):
    """One reviewed catalog heading; never drop unspecified real ingredients."""
    key = str(item.get('key') or item.get('ingredientId') or item.get('id') or '')
    return key == 'local:pl:67b936187af6ea892acb' and item.get('quantity') is None and not item.get('weight')
