#!/usr/bin/env python3
"""Build the ODbL offline price subset from public Open Prices evidence.

Inputs are explicit local downloads. No private receipts, credentials or network
access. API inputs are lists of expanded /api/v1/prices observations. The price
export provides additional loose-food observations, joined to the location export.
"""
import argparse
import ast
from collections import Counter, defaultdict
from datetime import date, timedelta
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_SPEC = importlib.util.spec_from_file_location('price_quantities', ROOT / 'custom_components/cook4me/price_quantities.py')
_QUANTITIES = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_QUANTITIES)


_SPEC_FORMS = importlib.util.spec_from_file_location('price_food_forms', ROOT / 'custom_components/cook4me/price_food_forms.py')
_FORMS = importlib.util.module_from_spec(_SPEC_FORMS)
_SPEC_FORMS.loader.exec_module(_FORMS)


def mapped_categories():
    tree = ast.parse((ROOT / 'custom_components/cook4me/automatic_prices.py').read_text())
    result = set()
    for node in tree.body:
        if isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple):
            for category, _kind, _names in ast.literal_eval(node.iter):
                result.add(category if ':' in category else 'en:' + category)
    return result


def rows(path):
    if path.suffix == '.gz':
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            yield from (json.loads(line) for line in stream)
    else:
        payload = json.loads(path.read_text(encoding='utf-8'))
        yield from payload['items'] if isinstance(payload, dict) else payload


def normalize(row, locations, categories, today):
    if row.get('duplicate_of') or row.get('price_is_discounted'):
        return None
    location = row.get('location')
    if not isinstance(location, dict):
        location = locations.get(row.get('location_id'), {})
    country = str(location.get('osm_address_country_code') or '').upper()
    currency = str(row.get('currency') or '').upper()
    if len(country) != 2 or len(currency) != 3:
        return None
    try:
        observed = date.fromisoformat(row['date'])
        amount = float(row['price'])
    except (KeyError, TypeError, ValueError):
        return None
    if not today - timedelta(days=180) <= observed <= today or not math.isfinite(amount) or amount <= 0:
        return None
    product = row.get('product') if isinstance(row.get('product'), dict) else {}
    kind, price_per = row.get('type'), str(row.get('price_per') or '').upper()
    tags = set(product.get('categories_tags') or []) if kind == 'PRODUCT' else {row.get('category_tag')}
    tags = {tag for tag in tags & categories if _FORMS.compatible_food_form(row, tag)}
    if not tags:
        return None
    if price_per == 'KILOGRAM':
        quantity, unit = 1, 'kg'
    elif kind == 'CATEGORY' and price_per == 'UNIT':
        quantity, unit = _FORMS.category_unit_basis(row)
    elif kind == 'PRODUCT' and price_per in {'', 'UNIT'}:
        quantity, unit = _QUANTITIES.explicit_product_basis(product)
    else:
        return None
    if not _FORMS.consistent_package_basis(row, quantity, unit):
        return None
    tags = {tag for tag in tags if _FORMS.compatible_category_basis(row, tag, unit)}
    if not tags:
        return None
    try:
        quantity = float(quantity)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(quantity) or quantity <= 0 or unit not in {'g', 'kg', 'ml', 'cl', 'l', 'pcs'}:
        return None
    return {'id': row['id'], 'barcode': row.get('product_code') or '', 'amount': amount,
            'currency': currency, 'basisQuantity': quantity, 'basisUnit': unit,
            'pricePer': price_per, 'usable': True, 'date': observed.isoformat(),
            'country': country, 'location': location.get('osm_name') or '',
            'productName': row.get('product_name') or product.get('product_name') or '',
            'source': 'open_prices', 'confidence': 'external_observation', 'categories': sorted(tags)}


def build(locations_path, prices_path, api_paths, today):
    categories = mapped_categories()
    locations = {r['id']: r for r in rows(locations_path)}
    by_country = defaultdict(list)
    for r in sorted(locations.values(), key=lambda r: (-(r.get('price_count') or 0), r['id'])):
        country = str(r.get('osm_address_country_code') or '').upper()
        if len(country) == 2 and r.get('price_count', 0) > 0:
            by_country[country].append(r['id'])
    best = {}
    examined = Counter()
    def add(raw):
        examined['rows'] += 1
        row = normalize(raw, locations, categories, today)
        if row is None:
            return
        examined['usable'] += 1
        base = 'g' if row['basisUnit'] in {'g', 'kg'} else 'ml' if row['basisUnit'] in {'ml', 'cl', 'l'} else 'pcs'
        for tag in row['categories']:
            key = (row['country'], row['currency'], tag, base)
            if key not in best or (row['date'], row['id']) > (best[key]['date'], best[key]['id']):
                best[key] = row
    # The export has numeric product IDs, not metadata: only CATEGORY is usable.
    for row in rows(prices_path):
        if row.get('type') == 'CATEGORY':
            add(row)
    for path in api_paths:
        for row in rows(path):
            add(row)
    observations = {r['id']: r for r in best.values()}
    # Keep only category assignments for which the row was selected.
    selected_tags = defaultdict(set)
    for (_, _, tag, _), row in best.items():
        selected_tags[row['id']].add(tag)
    for ident, row in observations.items():
        row['categories'] = sorted(selected_tags[ident])
    inputs = [locations_path, prices_path, *api_paths]
    return {'schemaVersion': 1, 'generatedAt': today.isoformat(),
            'attribution': 'Open Prices / Open Food Facts contributors; location data © OpenStreetMap contributors',
            'license': 'ODbL-1.0', 'licenseUrl': 'https://opendatacommons.org/licenses/odbl/1-0/',
            'sourceUrls': ['https://prices.openfoodfacts.org/data/locations.jsonl.gz',
                           'https://prices.openfoodfacts.org/data/prices.jsonl.gz',
                           'https://prices.openfoodfacts.org/api/v1/prices'],
            'inputs': [{'name': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in inputs],
            'locationsByCountry': dict(sorted(by_country.items())),
            'observations': sorted(observations.values(), key=lambda r: (r['country'], r['id'])),
            'buildCounts': dict(examined)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--locations', type=Path, required=True)
    parser.add_argument('--prices', type=Path, required=True)
    parser.add_argument('--api-prices', type=Path, action='append', default=[])
    parser.add_argument('--as-of', type=date.fromisoformat, default=date.today())
    parser.add_argument('--output', type=Path, default=ROOT / 'custom_components/cook4me/catalog/observed_prices.v1.json')
    args = parser.parse_args()
    data = build(args.locations, args.prices, args.api_prices, args.as_of)
    args.output.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    counts = Counter(r['country'] for r in data['observations'])
    print(json.dumps({'observations': len(data['observations']), 'countries': dict(counts), 'bytes': args.output.stat().st_size}))


if __name__ == '__main__':
    main()
