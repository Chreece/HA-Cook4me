#!/usr/bin/env python3
"""Audit unmeasured basic allowances separately from offline price evidence."""
import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import importlib
import json
from pathlib import Path

from audit_recipe_price_coverage_v90 import runtime, COMPONENT

BASE = 'c7bfaaf51c5db1e3cbd35ddce3d5b782d02b6d95'


def audit(component, package):
    quantities, ns = runtime(component, package)
    allowances = importlib.import_module(package + '.price_allowances')
    inventory = importlib.import_module(package + '.inventory')
    benchmarks = importlib.import_module(package + '.price_benchmarks')
    snapshot = importlib.import_module(package + '.price_snapshot')
    catalog = json.loads((component / 'catalog/merged_catalog.v1.json').read_text())
    by_id = {str(row['id']): row for row in catalog['ingredients']}
    references = defaultdict(list)
    today = date.today()
    for row in snapshot._load()['observations']:
        if row.get('country') != 'DE' or row.get('currency') != 'EUR' or not row.get('usable') or not row.get('basisQuantity'):
            continue
        if not today - timedelta(days=180) <= date.fromisoformat(row['date']) <= today:
            continue
        for category in row.get('categories', []):
            if category not in row.get('categoryExclusions', []) and snapshot.category_observation_allowed(row, category):
                references[category].append(row)
    total = Counter()
    by_name = defaultdict(Counter)
    gaps = defaultdict(Counter)
    examples = defaultdict(list)
    cache = {}
    for family in catalog['recipes']:
        for variant in family['variants']:
            ingredients = variant.get('ingredients', [])
            subset = [by_id[str(item['ingredientId'])] for item in ingredients if str(item.get('ingredientId')) in by_id]
            recipe = ns['canonical_recipe'](variant, subset)
            known = fallback = zero = 0
            for item in recipe['ingredients']:
                signature = json.dumps(item, sort_keys=True)
                if signature not in cache:
                    options = quantities.price_options(item)
                    category = ns['category_for'](item)
                    priced = bool(category) and any(inventory.convert_amount(1, option['unit'], ref['basisUnit']) is not None
                        for option in options for ref in references[category[0]])
                    estimate = bool(benchmarks.fallback_estimate(item, country='DE', currency='EUR')) if not priced else False
                    allowance = bool(allowances.zero_cost_allowance(item, 'EUR')) if not priced and not estimate else False
                    cache[signature] = priced, estimate, allowance, options
                priced, estimated, allowance, options = cache[signature]
                known += priced
                fallback += estimated
                zero += allowance
                name = item.get('canonicalName') or item.get('name', '')
                by_name[name]['known' if priced else 'fallback' if estimated else 'zeroAllowance' if allowance else 'missing'] += 1
                if not priced and not estimated and not allowance:
                    gaps[name][f"{item.get('unitKey', '')}|{item.get('unit', '')}|{'options' if options else 'no options'}"] += 1
                    if len(examples[name]) < 2:
                        examples[name].append({'variant': variant['variantId'], 'title': variant['title'], 'item': item})
            count = len(recipe['ingredients'])
            total.update(variants=1, ingredients=count, known=known, fallback=fallback, zeroAllowance=zero, covered=known+fallback+zero)
            total['knownComplete'] += known == count and count > 0
            total['budgetCompleteBeforeAllowance'] += known + fallback == count and count > 0
            total['budgetComplete'] += known + fallback + zero == count and count > 0
            total['variantsWithAllowance'] += zero > 0
            total['noKnownCost'] += known == 0
            total['noBudgetCost'] += known + fallback + zero == 0
    names = sorted(by_name, key=lambda name: by_name[name]['fallback'] + by_name[name]['missing'], reverse=True)
    return {'summary': dict(total), 'ingredients': {name: {
        **dict(by_name[name]), 'units': dict(gaps[name]), 'examples': examples[name]} for name in names}}



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(COMPONENT, '_prices99_audit')
    report = {'market': 'DE', 'currency': 'EUR', 'asOf': date.today().isoformat(),
        'baselineCommit': BASE,
        'method': 'Language/serving variants and ingredient occurrences, without household prices. Known price evidence is unchanged. Zero allowances count only toward estimated budgets; no amount or observed price is invented.',
        'summary': result['summary'],
        'allowances': [{'ingredient': name, 'occurrences': row['zeroAllowance']}
            for name, row in sorted(result['ingredients'].items(), key=lambda pair: pair[1].get('zeroAllowance', 0), reverse=True) if row.get('zeroAllowance')],
        'largestRemainingGaps': [{'ingredient': name, 'occurrences': row['missing']}
            for name, row in sorted(result['ingredients'].items(), key=lambda pair: pair[1].get('missing', 0), reverse=True)[:25]]}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report['summary'], indent=2))
