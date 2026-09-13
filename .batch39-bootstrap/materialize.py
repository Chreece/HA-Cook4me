#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, io, os, pathlib, tarfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHUNKS = ROOT / '.batch39-bootstrap' / 'chunks'
PAYLOAD_SHA = '93c8a6f3e8ce328cfae7b82b878f32464dbcedc07e9ebccfe06b18fbf2b228fb'
FILES = {
'docs/nutrition-review-batch39-bulk-families-v60.md': ('c8deaf86a8723cb8b843366d2cec414c5ff4c1a8f3efc66a8eefa44f0b6bc2eb', 0o644),
'tests/fixtures/nutrition-batch39-retained-reference-v60.json.gz': ('e0bfc5e21965153678a7897c91b546a6cf39b11450c5e06a5428449d556e6d46', 0o644),
'tests/test_release_catalog_nutrition_review_batch38_v60.py': ('c38225888a7efe3df490b10c8fb18d77d8734c793218debf52d43913edb94c5d', 0o644),
'tests/test_release_catalog_nutrition_review_batch39_v60.py': ('8838ab889ff74e5ae53131d9e96dc69379008c7a4882e82dc1973fee8303d9bc', 0o644),
'tools/classify_nutrition_review_queue_v60.py': ('90fe35c4ebc47fcc054c8b7b07082c8001baa764a0d50546e16340d17043a949', 0o755),
'tools/release_catalog_nutrition_bulk_family_rules_batch39.v1.json': ('f50e6ea02d753a1a50f8907ec36df14c9be0bf49fcd2143ad92b9b5c213a4d76', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_043.v1.json': ('50c8e649652aeadc9d7d4c355edac33e2754e67e97661b1a4259ffeb50c9a086', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_043b.v1.json': ('6f11eff75ac3c992c829a14c1f4eca166507f020fe9bc4f2b50177bc845247f9', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_043c.v1.json': ('a4829fa3a80adec528470e9fb03d532a25f7176ba16303611dc8e6ed93e518c3', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_043d.v1.json': ('53ca063af886c40a6dc3357d7fd23e41b85a017f5890e741ef410a1f51f0508a', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_043e.v1.json': ('6a3055d5b2171a877637c6664cd72b126039bab6dab9637d60556efbd0c2e940', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_043f.v1.json': ('c236ce83f981c7cbb0543f0678e5e5fa5e5fe466a7a4431c2bbeda5fd14edf23', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_043g.v1.json': ('5fa39c0195a1599c4ef3f626d6de20df1aa723168bcb7b1dbaa7c8f38d013842', 0o644),
}

def die(msg: str) -> None:
    raise SystemExit(msg)

def prefix(path: pathlib.Path, length: int) -> str:
    text = ''.join(path.read_text(encoding='ascii').split())
    if len(text) < length:
        die(f'transport too short: {path.name}')
    return text[:length]

chunks = sorted(CHUNKS.glob('chunk-*'))
if [p.name for p in chunks] != [f'chunk-{i:03d}' for i in range(21)]:
    die('expected exact Batch 39 prefix chunk set')
tail = ROOT / '.batch39-bootstrap' / 'tail-021-023.b64'
if not tail.is_file():
    die('missing Batch 39 tail transport')
parts = [prefix(path, 5800) for path in chunks]
parts.append(prefix(tail, 13524))
try:
    payload = base64.b64decode(''.join(parts), validate=True)
except Exception as exc:
    die(f'invalid base64 transport: {exc}')
if hashlib.sha256(payload).hexdigest() != PAYLOAD_SHA:
    die('payload sha256 mismatch')
with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as tf:
    members = tf.getmembers()
    if [m.name for m in members] != list(FILES):
        die('payload path set/order mismatch')
    for m in members:
        p = pathlib.PurePosixPath(m.name)
        if not m.isfile() or p.is_absolute() or '..' in p.parts:
            die(f'unsafe tar member: {m.name}')
        want_sha, want_mode = FILES[m.name]
        if (m.mode & 0o777) != want_mode:
            die(f'mode mismatch: {m.name}')
        src = tf.extractfile(m)
        if src is None:
            die(f'missing member bytes: {m.name}')
        data = src.read()
        if hashlib.sha256(data).hexdigest() != want_sha:
            die(f'file sha256 mismatch: {m.name}')
        dest = ROOT / m.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        os.chmod(dest, want_mode)
print(f'materialized {len(FILES)} Batch 39 files; payload sha256={PAYLOAD_SHA}')
