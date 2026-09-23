"""Verify the HACS source archive, including the active panel's import closure.

Only archived distribution files change. The checkout and catalog bytes do not.
No HA, credentials, inventory, provider, or live configuration are accessed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import tempfile
from time import perf_counter
import unittest
from urllib.request import Request, urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = 'custom_components/cook4me/'
FRONTEND = RUNTIME + 'frontend/'
DEVELOPMENT = ('tools/', 'tests/', 'docs/', 'scripts/', '.github/')
RETIRED_BUNDLE = re.compile(re.escape(FRONTEND) + r'cook4me-panel-v(\d+)-bundle\.js$')
IMPORTS = re.compile(r'''\b(?:import\s*(?:\(\s*)?|from\s*)["']([^"']+)["']''')


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def retired(path: str) -> bool:
    match = RETIRED_BUNDLE.fullmatch(path)
    return bool(match and int(match.group(1)) < 126)


def zip_members(data: bytes, *, github: bool = False) -> dict[str, bytes]:
    with ZipFile(io.BytesIO(data)) as archive:
        files = {}
        prefixes = set()
        for item in archive.infolist():
            if item.is_dir():
                continue
            name = item.filename
            if github:
                prefix, name = name.split('/', 1)
                prefixes.add(prefix)
            if name.startswith('/') or '..' in PurePosixPath(name).parts or name in files:
                raise AssertionError('Unsafe or duplicate archive path: ' + name)
            files[name] = archive.read(item)
        if github and len(prefixes) != 1:
            raise AssertionError('Expected one GitHub repository prefix')
        return files


def module_closure(files: dict[str, bytes], entry: str) -> set[str]:
    pending, seen = [entry], set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        if path not in files:
            raise AssertionError('Missing active frontend dependency: ' + path)
        seen.add(path)
        source = files[path].decode('utf-8')
        for specifier in IMPORTS.findall(source):
            if not specifier.startswith('.'):
                continue
            target = specifier.split('?', 1)[0].split('#', 1)[0]
            target = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
            if not target.startswith(RUNTIME):
                raise AssertionError('Frontend import leaves the runtime: ' + target)
            pending.append(target)
    return seen


def sizes(data: bytes) -> dict:
    with ZipFile(io.BytesIO(data)) as archive:
        files = [item for item in archive.infolist() if not item.is_dir()]
        return {'zip_bytes': len(data), 'files': len(files),
                'uncompressed_bytes': sum(item.file_size for item in files),
                'runtime_files': sum(item.filename.startswith(RUNTIME) for item in files),
                'runtime_bytes': sum(item.file_size for item in files if item.filename.startswith(RUNTIME)),
                'retired_bundles': sum(retired(item.filename) for item in files),
                'retired_bundle_bytes': sum(item.file_size for item in files if retired(item.filename))}


class HacsArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Worktree attributes permit testing the packaging change before commit.
        cls.source = {path: (ROOT/path).read_bytes() for path in
                      git('ls-files', '-z').decode().split('\0') if path}
        cls.zip = git('archive', '--format=zip', '--worktree-attributes', 'HEAD')
        cls.files = zip_members(cls.zip)
        panel = cls.source[RUNTIME+'panel.py'].decode()
        match = re.search(r'^_PANEL_MODULE\s*=\s*["\']([^"\']+)', panel, re.M)
        cls.entry = FRONTEND + match.group(1)

    def test_all_nonretired_runtime_files_are_present_and_byte_identical(self):
        expected = {p: v for p, v in self.source.items() if p.startswith(RUNTIME) and not retired(p)}
        actual = {p: v for p, v in self.files.items() if p.startswith(RUNTIME)}
        self.assertEqual(set(actual), set(expected))
        for path in expected:
            with self.subTest(path=path):
                self.assertEqual(hashlib.sha256(actual[path]).digest(), hashlib.sha256(expected[path]).digest())

    def test_hacs_metadata_license_and_readme_remain(self):
        for path in ('hacs.json', 'LICENSE', 'README.md', RUNTIME+'manifest.json'):
            self.assertEqual(self.files[path], self.source[path], path)
        self.assertFalse(json.loads(self.files['hacs.json']).get('zip_release', False),
                         'Do not switch update channels without a compatible release asset')

    def test_development_files_stay_in_git_not_in_download_archive(self):
        self.assertTrue(any(p.startswith('tools/') for p in self.source))
        self.assertTrue(any(p.startswith('tests/') for p in self.source))
        self.assertFalse(any(p.startswith(DEVELOPMENT) for p in self.files))

    def test_only_old_compiled_bundles_are_omitted_from_integration(self):
        removed = {p for p in self.source if p.startswith(RUNTIME)} - set(self.files)
        self.assertTrue(removed)
        self.assertTrue(all(retired(p) for p in removed))
        self.assertIn(FRONTEND+'cook4me-panel-v126-bundle.js', self.files)

    def test_every_reachable_frontend_module_survives(self):
        reachable = module_closure(self.source, self.entry)
        self.assertEqual(module_closure(self.files, self.entry), reachable)
        self.assertTrue(all(not retired(path) for path in reachable))

    def test_import_audit_detects_missing_static_and_dynamic_modules(self):
        entry = FRONTEND+'test.js'
        for statement in ["import './missing.js';", "import {x} from './missing.js';",
                          "await import('./missing.js?v=1');"]:
            with self.subTest(statement=statement), self.assertRaisesRegex(AssertionError, 'Missing active'):
                module_closure({entry: statement.encode()}, entry)

    def test_catalog_languages_and_assets_are_not_trimmed(self):
        for folder in ('catalog/', 'catalog_ui_locales/', 'translations/', 'frontend/assets/', 'brand/'):
            prefix = RUNTIME+folder
            expected = {p for p in self.source if p.startswith(prefix)}
            self.assertTrue(expected, folder)
            self.assertEqual({p for p in self.files if p.startswith(prefix)}, expected)


def report(baseline: str, output: Path, github_sha: str | None) -> None:
    current = git('archive', '--format=zip', '--worktree-attributes', 'HEAD')
    previous = git('archive', '--format=zip', baseline)
    current_files = zip_members(current)
    details = {'baseline': baseline, 'checkout': git('rev-parse', 'HEAD').decode().strip(),
               'before': sizes(previous), 'after': sizes(current),
               'scope': 'Distribution archive only; no live HA timing.'}
    details['zip_reduction_percent'] = round(100*(1-len(current)/len(previous)), 2)
    # Mirror the relevant HACS extraction step, without running the integration.
    for label, archive_bytes in [('before', previous), ('after', current)]:
        start = perf_counter()
        with tempfile.TemporaryDirectory(prefix='cook4me-hacs-audit-') as directory:
            with ZipFile(io.BytesIO(archive_bytes)) as archive:
                for item in archive.infolist():
                    if item.is_dir() or not item.filename.startswith(RUNTIME):
                        continue
                    destination = Path(directory)/item.filename[len(RUNTIME):]
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(archive.read(item))
            details[label]['runner_extract_seconds'] = round(perf_counter()-start, 3)
    if github_sha:
        if not re.fullmatch(r'[0-9a-f]{40}', github_sha):
            raise ValueError('A full commit SHA is required')
        # Public repository and fixed host; no credentials or external callbacks.
        url = f'https://codeload.github.com/Chreece/HA-Cook4me/zip/{github_sha}'
        request = Request(url, headers={'User-Agent': 'Cook4Me-packaging-audit'})
        start = perf_counter()
        with urlopen(request, timeout=120) as response:
            remote = response.read(100_000_001)
        if len(remote)>100_000_000:
            raise AssertionError('Unexpectedly large download')
        remote_files = zip_members(remote, github=True)
        if set(remote_files) != set(current_files):
            raise AssertionError('GitHub archive differs from local verified file set')
        for path in current_files:
            if remote_files[path] != current_files[path]:
                raise AssertionError('GitHub archive changed file contents: '+path)
        details['github_archive'] = {'sha': github_sha, 'zip_bytes': len(remote),
                                     'download_seconds_on_runner': round(perf_counter()-start, 3),
                                     'all_files_verified': len(remote_files)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(details, indent=2)+'\n')
    print(json.dumps(details, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path)
    parser.add_argument('--baseline', default='HEAD^')
    parser.add_argument('--github-sha')
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(HacsArchiveTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    if args.report:
        report(args.baseline, args.report, args.github_sha)
