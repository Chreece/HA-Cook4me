#!/usr/bin/env python3
"""Compare actual offline eligibility against v87, including both snapshot files.

Counts are catalog language/serving variants, not distinct recipe families.
Both sides execute their own quantity/category rules. No household prices.
"""
import argparse
import ast
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, timedelta
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components/cook4me'
BASE = '866252ba5ef03734c17afa5cf601ae9fbd9979a5'
EXAMPLES = {'805952', '314558', '963752', '785571', '270881', '879742', '288189'}


def runtime(path, name):
    package = types.ModuleType(name); package.__path__ = [str(path)]
    sys.modules[name] = package
    quantities = importlib.import_module(name + '.price_measurements')
    units = importlib.import_module(name + '.price_units')
    namespace = dict(deepcopy=deepcopy, price_ingredient=units.price_ingredient)
    if (path / 'price_identity.py').exists():
        identity = importlib.import_module(name + '.price_identity')
        namespace.update(pricing_name=identity.pricing_name, is_cost_heading=identity.is_cost_heading)
    tree = ast.parse((path / 'automatic_prices.py').read_text())
    tree.body = [n for n in tree.body if isinstance(n, ast.For)
                 or isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_CATEGORIES' for t in n.targets)
                 or isinstance(n, ast.FunctionDef) and n.name in {'category_for', 'canonical_recipe'}]
    exec(compile(tree, str(path / 'automatic_prices.py'), 'exec'), namespace)
    return quantities, namespace


def audit(path, package, catalog, today):
    quantities, ns = runtime(path, package)
    inventory = importlib.import_module(package + '.inventory')
    references = defaultdict(list)
    for filename in ['observed_prices.v1.json', 'retail_prices.v1.json']:
        for row in json.loads((path / 'catalog' / filename).read_text())['observations']:
            if row['country'] == 'DE' and row['currency'] == 'EUR' and row.get('usable') and row.get('basisQuantity') \
                    and today - timedelta(days=180) <= date.fromisoformat(row['date']) <= today:
                for tag in row['categories']: references[tag].append(row)
    names = {row['id']: row['canonicalName'] for row in catalog['ingredients']}
    summary = defaultdict(Counter); missing = Counter(); examples = []; cache = {}
    for recipe in catalog['recipes']:
        for variant in recipe['variants']:
            covered = water = food = 0; gaps = []
            # Supplying canonical names here avoids rebuilding the full lookup for every recipe.
            canonical = ns['canonical_recipe']({'ingredients': [
                {**raw, 'canonicalName': names.get(raw.get('ingredientId'), raw.get('name', ''))}
                for raw in variant.get('ingredients', [])]}, [])
            rows = canonical['ingredients']
            for item in rows:
                signature = json.dumps(item, sort_keys=True)
                if signature not in cache:
                    options = quantities.price_options(item); category = ns['category_for'](item)
                    priced = bool(category) and any(inventory.convert_amount(1, option['unit'], ref['basisUnit']) is not None
                        for option in options for ref in references[category[0]])
                    cache[signature] = priced, 'amount missing/unsupported' if not options else 'price/unit missing'
                priced, reason = cache[signature]
                covered += priced
                if item['canonicalName'].casefold() in {'water', 'tap water'}: water += priced
                else: food += priced
                if not priced:
                    missing[item['canonicalName']] += 1
                    gaps.append({'name': item['canonicalName'], 'reason': reason})
            status = 'complete' if rows and covered == len(rows) else 'partial' if covered else 'noCost'
            for language in ['all', variant.get('language', 'unknown')]:
                summary[language][status] += 1
                summary[language]['pricedIngredients'] += covered
                summary[language]['pricedFoodIngredients'] += food
                summary[language]['pricedWaterIngredients'] += water
                summary[language]['totalIngredients'] += len(rows)
            if str(variant.get('variantId') or variant.get('id') or variant.get('variantFunctionalId')) in EXAMPLES:
                examples.append({'id': variant.get('variantId') or variant.get('id') or variant.get('variantFunctionalId'),
                    'title': variant.get('title') or recipe.get('title'), 'priced': covered, 'total': len(rows), 'status': status, 'missing': gaps})
    return {'summary': dict(summary), 'largestMissing': missing.most_common(25), 'examples': examples}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default=BASE)
    parser.add_argument('--as-of', default=date.today().isoformat())
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    catalog = json.loads((COMPONENT / 'catalog/merged_catalog.v1.json').read_text())
    with tempfile.TemporaryDirectory() as directory:
        before = Path(directory); (before / 'catalog').mkdir()
        for filename in ['automatic_prices.py', 'price_measurements.py', 'price_units.py', 'inventory.py',
                         'price_identity.py', 'catalog/price_densities.v1.json', 'catalog/price_portions.v1.json', 'catalog/observed_prices.v1.json', 'catalog/retail_prices.v1.json']:
            (before / filename).write_bytes(subprocess.check_output(['git', 'show', args.base + ':custom_components/cook4me/' + filename], cwd=ROOT))
        result = {'market': 'DE', 'currency': 'EUR', 'asOf': args.as_of, 'base': args.base, 'variantCounts': True,
                  'results': {label: audit(path, '_audit88_' + label, catalog, date.fromisoformat(args.as_of))
                              for label, path in [('before', before), ('after', COMPONENT)]}}
    if args.output: args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({label: {lang: data['summary'][lang] for lang in ['all', 'de']} for label, data in result['results'].items()}, indent=2))
    print(json.dumps({label: data['examples'] for label, data in result['results'].items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
