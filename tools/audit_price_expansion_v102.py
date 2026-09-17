#!/usr/bin/env python3
"""Compare reference, rough-budget and zero-allowance coverage with v101."""
import argparse
from datetime import date
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

from audit_price_allowances_v99 import audit, COMPONENT

BASE = 'b7fd2c9f122fb7c9c009e018a5349fb0df40b05b'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before-json', type=Path, help='Reuse a full baseline audit of BASE')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.before_json:
        before = json.loads(args.before_json.read_text())
    else:
        with tempfile.TemporaryDirectory(prefix='cook4me-prices-v102-') as directory:
            archive = subprocess.check_output(['git', 'archive', BASE, 'custom_components/cook4me'], cwd=COMPONENT.parents[1])
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(directory, filter='data')
            before = audit(Path(directory) / 'custom_components/cook4me', '_prices102_before')
    after = audit(COMPONENT, '_prices102_after')
    metrics = ['known', 'fallback', 'zeroAllowance', 'missing']
    changed = []
    for name, row in after['ingredients'].items():
        old = before['ingredients'].get(name, {})
        delta = {key: row.get(key, 0) - old.get(key, 0) for key in metrics}
        if any(delta.values()):
            changed.append({'ingredient': name, 'before': {key: old.get(key, 0) for key in metrics},
                            'after': {key: row.get(key, 0) for key in metrics}, 'delta': delta})
    report = {'market': 'DE', 'currency': 'EUR', 'asOf': date.today().isoformat(), 'baselineCommit': BASE,
              'method': 'Counts are language/serving variants and ingredient occurrences, without household prices. Each build uses its own identities, quantities and eligible dated references. Rough budgets and unmeasured zero allowances are separate from reference coverage.',
              'before': before['summary'], 'after': after['summary'],
              'delta': {key: value - before['summary'][key] for key, value in after['summary'].items()},
              'changedIngredients': sorted(changed, key=lambda row: row['delta']['known'], reverse=True),
              'nextReferenceGaps': [{'ingredient': name, 'fallback': row.get('fallback', 0), 'missing': row.get('missing', 0)}
                  for name, row in sorted(after['ingredients'].items(), key=lambda pair: pair[1].get('fallback', 0), reverse=True)[:30]]}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['before', 'after', 'delta']}, indent=2))
