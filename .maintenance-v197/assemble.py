#!/usr/bin/env python3
"""Assemble the audited merge using exact Git objects and reviewed text deltas.

One-shot maintenance on chore/consolidate-v197 only. Does not update main or
remove refs. The final source is checked against locally tested blob hashes.
"""
import argparse
from pathlib import Path, PurePosixPath
import json
import subprocess
import zipfile

ROOT = Path.cwd()
def git(*args, input=None, check=True):
    return subprocess.run(['git', *args], input=input, capture_output=True, text=True, check=check)
def blob(path):
    r = git('rev-parse', 'HEAD:' + path, check=False)
    return r.stdout.strip() if not r.returncode else None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--audit-dir', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    with zipfile.ZipFile(args.inputs) as z:
        if z.namelist() != ['inputs.json']:
            raise ValueError('Unexpected input archive paths')
        data = json.loads(z.read('inputs.json'))
    assert data['repository'] == 'Chreece/HA-Cook4me' and data['schemaVersion'] == 1
    audit = json.loads((args.audit_dir / 'branch-audit.json').read_text())
    assert audit['main'] == data['base']
    assert len(audit['branches']) == 287
    if args.verify:
        for row in data['files']:
            path = ROOT / row['path']
            if row['final'] is None:
                assert not path.exists(), row['path']
            else:
                assert path.is_file(), row['path']
                actual = git('hash-object', str(path)).stdout.strip()
                assert actual == row['final'], (row['path'], actual, row['final'])
        print('All', len(data['files']), 'reviewed output paths match tested Git hashes')
        return
    assert git('merge-base', '--is-ancestor', data['base'], 'HEAD', check=False).returncode == 0
    for row in data['files']:
        path = PurePosixPath(row['path'])
        if path.is_absolute() or '..' in path.parts or path.parts[0] not in {'custom_components', 'tests', 'tools', 'docs', '.github'}:
            raise ValueError('Unexpected target path')
        if path.parts[0] == '.github' and str(path) != '.github/workflows/consolidation-regressions.yml':
            raise ValueError('Unreviewed workflow change')
        assert blob(str(path)) == row['expected'], ('Base file moved', str(path))
        dest = ROOT / str(path)
        if row['source']:
            dest.parent.mkdir(parents=True, exist_ok=True)
            content = subprocess.check_output(['git', 'cat-file', 'blob', row['source']])
            dest.write_bytes(content)
        elif not row.get('generate') and dest.exists():
            dest.unlink()
    patch = Path('/tmp/cook4me-consolidation-v197.patch')
    patch.write_text(data['patch'])
    git('apply', '--check', str(patch))
    git('apply', str(patch))
    rows = []
    for r in audit['branches']:
        rows.append({
            'branch': r['branch'], 'sha': r['sha'],
            'classification': data.get('classificationOverrides', {}).get(r['branch'], r['status']),
            'prs': r.get('prs', []),
            'resolution': data['auditResolutions'].get(r['branch'], data['auditManifestDefaultResolution']),
        })
    report = {
        'schemaVersion': 1, 'repository': data['repository'], 'auditedMain': data['base'],
        'originalBranchCount': 287, 'backupRunId': 35853194745, 'backupArtifactId': 10746870064,
        'branches': rows, 'policy': data['auditManifestPolicy'],
    }
    (ROOT / 'docs/BRANCH_CONSOLIDATION_V197.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('Applied reviewed source delta; catalog reconstruction and tests must run before publication')

if __name__ == '__main__':
    main()
