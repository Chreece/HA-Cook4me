"""Produce the reported recipe's translated detail and real offline cost."""
import asyncio
import importlib
import json
from pathlib import Path
import sys

from test_price_fixes_v104 import PriceFixTests


async def main(output):
    PriceFixTests.setUpClass()
    case = PriceFixTests()
    case.setUp()
    try:
        release = importlib.import_module(case.prices.__package__ + '.release_catalog')
        await release.async_warm_release_catalog(case.hass)
        recipe = release.recipe_by_variant('314559', language='el', configured_language='el', country='DE')
        cost = await case.prices.offline_recipe_price(case.bridge, recipe, case.catalog['ingredients'])
        assert cost['budgetTotalsByCurrency'] == {'EUR': 2.12}
        output.write_text(json.dumps({'recipe': recipe, 'cost': cost}, ensure_ascii=False, indent=2) + '\n')
        print(cost['budgetTotalsByCurrency'])
    finally:
        await case.asyncTearDown()
        case.doCleanups()


if __name__ == '__main__':
    asyncio.run(main(Path(sys.argv[1])))
