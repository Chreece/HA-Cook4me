"""Produce browser fixtures through the real offline calculator."""
import asyncio
from copy import deepcopy
import json
from pathlib import Path
import sys

from test_price_allowances_v99 import PriceAllowanceTests


async def main(output):
    PriceAllowanceTests.setUpClass()
    case = PriceAllowanceTests('test_basics_are_explicit_zero_budget_without_known_coverage')
    case.setUp()
    try:
        fixtures = []
        async def add(key, title, ingredients, **extra):
            recipe = {'id': 'v99-' + key, 'title': title, 'servings': 2, 'language': 'en',
                      'ingredients': ingredients, 'mealTypes': ['main'], **extra}
            original = deepcopy(recipe)
            cost = await case.prices.offline_recipe_price(case.bridge, recipe, [])
            assert recipe == original
            fixtures.append({'key': key, 'recipe': recipe, 'cost': cost})
        rice = {'name': 'Rice', 'quantity': 250, 'unit': 'g'}
        await add('reference', 'Rice · price references', [rice])
        store = await case.store()
        await store.async_set_reference('n:rice', amount=1, currency='EUR', basis_quantity=100,
                                        basis_unit='g', country='DE', source='manual')
        await add('personal', 'Rice · saved price', [rice])
        await add('assumed', 'Seasoned rice · basic allowances', [rice, {'name': 'Salt'}, {'name': 'Pepper'}, {'name': 'Water'}],
                  match={'requiresSubstitutions': True, 'substitutions': [{'ingredientIndex': 0, 'original': 'Rice', 'replacement': {'key': 'chickpeas', 'name': 'Chickpeas'}}]})
        await add('partial', 'Saffron rice · quantity missing', [rice, {'name': 'Saffron'}])
        await add('unavailable', 'Saffron · no quantity', [{'name': 'Saffron'}])
        await add('rough', 'Radish · comparable food estimate', [{'name': 'Radish', 'quantity': 70, 'unit': 'g'}])
        await add('zero', 'Salt and water · zero allowance', [{'name': 'Salt'}, {'name': 'Water'}])
        output.write_text(json.dumps(fixtures, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({row['key']: row['cost']['priceConfidence'] for row in fixtures}))
    finally:
        await case.asyncTearDown()
        case.doCleanups()


if __name__ == '__main__':
    asyncio.run(main(Path(sys.argv[1])))
