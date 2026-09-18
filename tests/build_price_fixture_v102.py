"""Render-ready evidence from the real offline calculator, without network."""
import asyncio
import json
from pathlib import Path
import sys

from test_price_expansion_v102 import PriceExpansionTests


async def main(output):
    PriceExpansionTests.setUpClass()
    case = PriceExpansionTests('test_package_costs_and_portion_estimates')
    case.setUp()
    try:
        recipe = {'id': 'v102-evidence', 'title': 'Price reference examples', 'servings': 2,
                  'ingredients': [{'name': name, 'quantity': quantity, 'unit': unit}
                      for name, quantity, unit in [('Coconut cream', 400, 'ml'), ('Split pea', 100, 'g'),
                                                  ('Shiitake mushroom', 2, 'pcs'), ('Radish', 100, 'g'),
                                                  ('Coconut cream', 15, 'g')]]}
        cost = await case.prices.offline_recipe_price(case.bridge, recipe, [])
        assert cost['complete'] and cost['priceConfidence'] == 'reference'
        output.write_text(json.dumps({'recipe': recipe, 'cost': cost}, ensure_ascii=False, indent=2) + '\n')
        print(cost['totalsByCurrency'])
    finally:
        await case.asyncTearDown()
        case.doCleanups()


if __name__ == '__main__':
    asyncio.run(main(Path(sys.argv[1])))
