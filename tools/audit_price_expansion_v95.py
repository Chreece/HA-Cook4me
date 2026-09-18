#!/usr/bin/env python3
"""Compare offline ingredient coverage with v94 using authoritative identities."""
import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import importlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

from audit_recipe_price_coverage_v90 import runtime, COMPONENT

BASE = '978f4e5511f7d648e4c17909746b3d8973f74ef4'


def audit(component, package):
    quantities, ns = runtime(component, package)
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
            known = fallback = 0
            for item in recipe['ingredients']:
                signature = json.dumps(item, sort_keys=True)
                if signature not in cache:
                    options = quantities.price_options(item)
                    category = ns['category_for'](item)
                    priced = bool(category) and any(inventory.convert_amount(1, option['unit'], ref['basisUnit']) is not None
                        for option in options for ref in references[category[0]])
                    estimate = bool(benchmarks.fallback_estimate(item, country='DE', currency='EUR')) if not priced else False
                    cache[signature] = priced, estimate, options
                priced, estimated, options = cache[signature]
                known += priced
                fallback += estimated
                name = item.get('canonicalName') or item.get('name', '')
                by_name[name]['known' if priced else 'fallback' if estimated else 'missing'] += 1
                if not priced:
                    gaps[name][f"{item.get('unitKey', '')}|{item.get('unit', '')}|{'options' if options else 'no options'}"] += 1
                    if len(examples[name]) < 2:
                        examples[name].append({'variant': variant['variantId'], 'title': variant['title'], 'item': item})
            count = len(recipe['ingredients'])
            total.update(variants=1, ingredients=count, known=known, fallback=fallback, covered=known+fallback)
            total['knownComplete'] += known == count and count > 0
            total['budgetComplete'] += known + fallback == count and count > 0
            total['noKnownCost'] += known == 0
            total['noBudgetCost'] += known + fallback == 0
    names = sorted(by_name, key=lambda name: by_name[name]['fallback'] + by_name[name]['missing'], reverse=True)
    return {'summary': dict(total), 'ingredients': {name: {
        **dict(by_name[name]), 'units': dict(gaps[name]), 'examples': examples[name]} for name in names}}


def compact_report(result):
    """Keep published evidence small; full ingredient diagnostics are optional."""
    report = {k: v for k, v in result.items() if k not in {'before', 'after'}}
    for key in ('before', 'after'):
        if key in result:
            report[key] = {'summary': result[key]['summary']}
    after = result['after']['ingredients']
    before = result.get('before', {}).get('ingredients', {})
    changes = []
    for name, row in after.items():
        old = before.get(name, {})
        gain = row.get('known', 0) - old.get('known', 0)
        if before and gain:
            changes.append({'ingredient': name, 'additionalPriceReferences': gain,
                            'before': {k: old.get(k, 0) for k in ('known', 'fallback', 'missing')},
                            'after': {k: row.get(k, 0) for k in ('known', 'fallback', 'missing')}})
    report['changes'] = sorted(changes, key=lambda row: row['additionalPriceReferences'], reverse=True)
    report['largestRemainingGaps'] = [{'ingredient': name, 'missing': row.get('missing', 0)}
        for name, row in sorted(after.items(), key=lambda pair: pair[1].get('missing', 0), reverse=True)[:25]]
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current-only', action='store_true')
    parser.add_argument('--details', action='store_true', help='Include full per-ingredient diagnostics')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {'market': 'DE', 'currency': 'EUR', 'asOf': date.today().isoformat(), 'baselineCommit': BASE,
              'method': 'Counts are language/serving variants and ingredient occurrences; no household prices. Each build uses its own identities, conversions, source-form filters and dated references.'}
    if not args.current_only:
        with tempfile.TemporaryDirectory(prefix='cook4me-prices-v95-') as directory:
            archive = subprocess.check_output(['git', 'archive', BASE, 'custom_components/cook4me'], cwd=COMPONENT.parents[1])
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(directory, filter='data')
            result['before'] = audit(Path(directory) / 'custom_components/cook4me', '_prices95_before')
    result['after'] = audit(COMPONENT, '_prices95_after')
    args.output.write_text(json.dumps(result if args.details else compact_report(result), ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: result[key]['summary'] for key in ('before', 'after') if key in result}, indent=2))
