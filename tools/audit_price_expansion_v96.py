#!/usr/bin/env python3
"""Compare offline ingredient coverage with v95 using authoritative identities."""
import argparse
from datetime import date
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

from audit_price_expansion_v95 import audit, compact_report, COMPONENT

BASE = '02f32ba39784453819547aef0eace031f0e22d02'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--current-only', action='store_true')
    parser.add_argument('--details', action='store_true', help='Include full per-ingredient diagnostics')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {'market': 'DE', 'currency': 'EUR', 'asOf': date.today().isoformat(), 'baselineCommit': BASE,
              'method': 'Counts are language/serving variants and ingredient occurrences; no household prices. Each build uses its own identities, conversions, source-form filters and dated references.'}
    if not args.current_only:
        with tempfile.TemporaryDirectory(prefix='cook4me-prices-v96-') as directory:
            archive = subprocess.check_output(['git', 'archive', BASE, 'custom_components/cook4me'], cwd=COMPONENT.parents[1])
            with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
                tar.extractall(directory, filter='data')
            result['before'] = audit(Path(directory) / 'custom_components/cook4me', '_prices96_before')
    result['after'] = audit(COMPONENT, '_prices96_after')
    args.output.write_text(json.dumps(result if args.details else compact_report(result), ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: result[key]['summary'] for key in ('before', 'after') if key in result}, indent=2))
