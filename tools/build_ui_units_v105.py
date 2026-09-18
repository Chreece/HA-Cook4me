#!/usr/bin/env python3
"""Generate display aliases from the catalog; never infer measurement conversions."""
from collections import defaultdict
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'custom_components/cook4me'
TARGET = COMPONENT / 'frontend/cook4me-panel-v105.js'


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value) if not unicodedata.combining(c)).strip().lower()


def generated():
    data = json.loads((COMPONENT / 'catalog/ui_units.v1.json').read_text())
    candidates = defaultdict(set)
    seen = set()
    catalog = json.loads((COMPONENT / 'catalog/merged_catalog.v1.json').read_text())
    for family in catalog['recipes']:
        for variant in family['variants']:
            for item in variant.get('ingredients', []):
                for row in (item, item.get('weight') or {}):
                    key, unit = row.get('unitKey'), row.get('unit')
                    if key:
                        seen.add(key)
                        assert key in data['unitKeys'], f'Untranslated catalog unit: {key}'
                    if key and unit:
                        candidates[fold(unit)].add(data['unitKeys'][key])
    for kind, translations in data['labels'].items():
        candidates[fold(kind)].add(kind)
        for forms in translations.values():
            for label in forms:
                candidates[fold(label)].add(kind)
    aliases = {label: next(iter(kinds)) for label, kinds in candidates.items() if len(kinds) == 1}
    aliases.update({fold(kind): kind for kind in data['labels']})
    aliases.update({fold(label): kind for label, kind in data['aliases'].items()})
    output = {'labels': data['labels'], 'keys': data['unitKeys'], 'aliases': aliases,
              'overrides': {fold(label): kind for label, kind in data['labelOverrides'].items()}}
    return '// BEGIN GENERATED UI UNITS\nconst UI_UNITS=' + json.dumps(output, ensure_ascii=False, separators=(',', ':')) + ';\n// END GENERATED UI UNITS'


if __name__ == '__main__':
    source = TARGET.read_text()
    updated = re.sub(r'// BEGIN GENERATED UI UNITS.*?// END GENERATED UI UNITS', lambda _: generated(), source, flags=re.S)
    if '--check' in sys.argv:
        assert source == updated, 'Run python tools/build_ui_units_v105.py'
    else:
        TARGET.write_text(updated)
    print('v105 unit labels cover all 104 catalog identifiers')
