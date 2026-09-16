"""Reviewed provider identities used only for costing, never cooking data."""

# The provider's English name "Pepper" covers three different foods. Only the
# confirmed Pfeffer/Poivre identity may use ground black pepper references.
_NAMES = {'M_FOOD_388': 'ground black pepper', 'M_FOOD_131': 'tomato paste'}


# Exact reviewed preparation aliases. No substring stripping of cooked, dried,
# powdered, pickled, mixed or unspecified foods. Used only for cost lookup.
_ALIASES = {'chopped onion': 'onion',
 'diced onion': 'onion',
 'finely chopped onion': 'onion',
 'sliced onion': 'onion',
 'onion, peeled and chopped': 'onion',
 'onion, peeled and finely chopped': 'onion',
 'onion, peeled and thinly sliced': 'onion',
 'peeled thinly sliced onion': 'onion',
 'onions, peeled and quartered': 'onion',
 'onions, peeled and chopped': 'onion',
 'peeled finely chopped onion': 'onion',
 'red onion, peeled and thinly sliced': 'red onion',
 'red onion, finely chopped': 'red onion',
 'chopped red onion': 'red onion',
 'peeled carrot': 'carrot',
 'carrots, peeled and sliced into rounds': 'carrot',
 'carrots, peeled and cut into pieces': 'carrot',
 'peeled diced carrots': 'carrot',
 'carrot, peeled and cut into strips': 'carrot',
 'carrots, peeled and cut into tagliatelle-like strips': 'carrot',
 'carrot, peeled and cut into tagliatelle-like strips': 'carrot',
 'diced carrot': 'carrot',
 'sliced carrots': 'carrot',
 'minced garlic': 'garlic',
 'chopped garlic': 'garlic',
 'peeled and chopped garlic': 'garlic',
 'garlic, peeled, germ removed and chopped': 'garlic',
 'peeled garlic': 'garlic',
 'garlic, peeled and chopped': 'garlic',
 'peeled chopped garlic': 'garlic',
 'garlic, peeled and germ removed': 'garlic',
 'potatoes, peeled and diced': 'potato',
 'potatoes, peeled and halved': 'potato',
 'shallot, peeled and finely chopped': 'shallot',
 'chopped shallot': 'shallot',
 'finely chopped shallot': 'shallot',
 'raw red beetroot, peeled and cut into long strips': 'raw beetroot',
 'raw beetroot, peeled and cut into strips': 'raw beetroot',
 'parsnip, peeled and sliced into rounds': 'parsnip',
 'jerusalem artichoke, peeled and diced': 'jerusalem artichoke',
 'ground cinnamon': 'cinnamon',
 'lightly salted butter': 'butter',
 'grated cheese': 'cheese',
 'tablespoon of olive oil': 'olive oil',
 'tablespoon of sesame oil': 'sesame oil',
 'tablespoon of soy sauce': 'soy sauce',
 'tablespoon of mirin': 'mirin'}

def pricing_name(item):
    key = str(item.get('key') or item.get('ingredientId') or item.get('foodKey') or item.get('id') or '')
    name = _NAMES.get(key, str(item.get('canonicalName') or item.get('name') or '').strip().casefold())
    return _ALIASES.get(name, name)


def is_cost_heading(item):
    """One reviewed catalog heading; never drop unspecified real ingredients."""
    key = str(item.get('key') or item.get('ingredientId') or item.get('id') or '')
    return key == 'local:pl:67b936187af6ea892acb' and item.get('quantity') is None and not item.get('weight')


def reviewed_recipe_ingredient(item, recipe):
    """Source-confirmed food forms, scoped to their recipe variants.

    Tefal's Czech recipe calls the liquid row tofu cream and the mass row smoked
    tofu. Never infer liquid tofu is cream elsewhere; keep cooking data intact.
    https://www.tefal.cz/recepty/detail/index/source/PRO/id/287823/
    https://www.tefal.cz/recepty/detail/index/source/PRO/id/287825/
    https://www.krups.at/rezepte/detail/PRO/One-pot-Pasta%2Bmit%2Bger%2BTofu/1018279
    """
    variant = str(recipe.get('variantId') or recipe.get('variantFunctionalId')
                  or recipe.get('recipeFunctionalId') or recipe.get('id') or '')
    key = str(item.get('key') or item.get('ingredientId') or '')
    if (variant in {'287823', '287824', '287825', '317074', '317075', '317076'} and key == 'M_FOOD_477'
            and (item.get('unitKey') == 'UNIT_35' or item.get('unit') == 'ml')):
        return {**item, 'key': 'cook4me:recipe-tofu-cream', 'name': 'Tofu cream',
                'canonicalName': 'soy cooking cream'}
    # Czech source explicitly says cooked flageolet beans. The German recipe
    # is the same pasta preparation, with its own reviewed flageolet identity.
    if ((variant in {'287823', '287824', '287825'} and key == 'M_FOOD_233')
            or (variant in {'317074', '317075', '317076'} and key == 'local:de:61aaf81b774f8e119771')):
        return {**item, 'key': 'cook4me:recipe-cooked-flageolets',
                'name': 'Cooked flageolet beans', 'canonicalName': 'cooked flageolet beans'}
    return item
