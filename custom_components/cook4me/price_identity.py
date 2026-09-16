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


def reviewed_recipe_ingredient(item, recipe):
    """One source-confirmed form collision, scoped to its recipe variants.

    Tefal's Czech recipe calls the liquid row tofu cream and the mass row smoked
    tofu. Never infer liquid tofu is cream elsewhere; keep cooking data intact.
    https://www.tefal.cz/recepty/detail/index/source/PRO/id/287823/
    https://www.tefal.cz/recepty/detail/index/source/PRO/id/287825/
    """
    variant = str(recipe.get('variantId') or recipe.get('variantFunctionalId')
                  or recipe.get('recipeFunctionalId') or recipe.get('id') or '')
    key = str(item.get('key') or item.get('ingredientId') or '')
    if (variant in {'287823', '287824', '287825'} and key == 'M_FOOD_477'
            and (item.get('unitKey') == 'UNIT_35' or item.get('unit') == 'ml')):
        return {**item, 'key': 'cook4me:recipe-tofu-cream', 'name': 'Tofu cream',
                'canonicalName': 'soy cooking cream'}
    return item
