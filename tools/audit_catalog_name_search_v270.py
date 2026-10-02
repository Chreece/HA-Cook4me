"""Audit the shipped catalog's food-name search without editing source evidence."""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import sys
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'cook4me_name_audit_v270'
package = ModuleType(PACKAGE)
package.__path__ = [str(ROOT / 'custom_components' / 'cook4me')]
sys.modules[PACKAGE] = package
catalog = importlib.import_module(PACKAGE + '.release_catalog')
search = importlib.import_module(PACKAGE + '.catalog_name_search')


def audit() -> dict:
    queries = ['Pfeffer', 'Natron', 'lemon', 'chocolate', 'apple', 'nutmeg',
               'Salz', 'Spargel', 'ground black pepper', 'canned tomatoes']
    report = {'version': 270, 'scope': 'Food-name search; not identity, diet or nutrition reassignment',
              'languages': {}, 'queries': {}}
    for language in ('el', 'de', 'en'):
        rows = catalog.ingredient_choices(language)
        aliases = {alias for row in rows for alias in row['searchAliases']}
        projected = {alias: search.food_name_alias(alias) for alias in aliases}
        report['languages'][language] = {
            'ingredients': len(rows), 'uniqueRawAliases': len(aliases),
            'aliasesWithAnnotationOrClauseRemoved': sum(projected[a] != search.normalize_name_search(a) for a in aliases),
            'rowsWithAtLeastOneProjectedAlias': sum(any(projected[a] != search.normalize_name_search(a) for a in row['searchAliases']) for row in rows),
        }
        if language != 'el':
            continue
        for query in queries:
            words = search.normalize_name_search(query).split()
            old = [row for row in rows if all(any(word in search.normalize_name_search(alias)
                   for alias in [row['name'], row['canonicalName'], *row['searchAliases']]) for word in words)]
            new = [row for row in rows if any(all(any(token.startswith(word) for token in search.name_search_tokens(alias))
                   for word in words) for alias in row['nameSearchAliases'])]
            ids = {row['ingredientId'] for row in new}
            removed = [{'id': row['ingredientId'], 'name': row['canonicalName'],
                        'rawMatchingAliases': [alias for alias in row['searchAliases']
                                              if all(word in search.normalize_name_search(alias) for word in words)]}
                       for row in old if row['ingredientId'] not in ids]
            report['queries'][query] = {'before': len(old), 'after': len(new),
                                       'currentNames': [row['canonicalName'] for row in new],
                                       'removedFromSearch': removed}
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'languages': report['languages'], 'queries': {key: {'before': value['before'], 'after': value['after']}
                     for key, value in report['queries'].items()}}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
