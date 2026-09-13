#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, io, os, pathlib, tarfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CHUNKS = ROOT / '.batch38-bootstrap' / 'chunks'
PAYLOAD_SHA = '986b59d402246f123438c4d3494afe31ac7f6084f3187c2685a10cbcadfe02c4'
FILES = {
'docs/nutrition-review-batch38-bulk-families-v60.md': ('9e255907664ecf2ed32f2c7c146ba805180d329c6bfcb3dfe06f23a0f144ad13', 0o644),
'tests/fixtures/nutrition-batch38-retained-reference-v60.json.gz': ('b3141930a1b3424f1162069ce152028fc99fd991aa5e9388a1127247fc4bb7d4', 0o644),
'tests/test_release_catalog_nutrition_review_batch37_v60.py': ('602128578e44e9738da4442562c4a00347cb209a6984c032a8165a5d29c5e36b', 0o644),
'tests/test_release_catalog_nutrition_review_batch38_v60.py': ('8149277578c2285c1aa0781635ddd60712aec77edc86721ac6ebcefbc2fa04c8', 0o644),
'tools/classify_nutrition_review_queue_v60.py': ('b018fc586d82c21af9273e0bddaa788bf51c36bf256c5c50189a120fb7ce7bf6', 0o755),
'tools/release_catalog_nutrition_bulk_family_rules_batch38.v1.json': ('9f922d8e2039aadc4456315cfb34e146284d6e0a720d192c682d6204535d833b', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_042.v1.json': ('f36930e86dfb47dd7505639c3a559622a933e937a660957e9a7008298128207b', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_042b.v1.json': ('34774620bb840a594e168e9ba9bb6f0506b60e3f1dffdfcd7a29de8c0230d26a', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_042c.v1.json': ('0f3fd7c6a77206297ce02890e3f42a9ed6b34cc0b45f1474aa726710b7e25ccd', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_042d.v1.json': ('5e1f6fe64b778a622ef33ea50f526dd703b50777dc682bc327960d0d190dace6', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_042e.v1.json': ('71b7108da772836fb0f85b1e7f2ccda038ba2c87c9e246fc4d364731ed930b1a', 0o644),
'tools/release_catalog_reviewed_nutrition_targets_042f.v1.json': ('a17c0ec0cec65a2a55c9bd30e0d6dc2e073ea802e24bc45bc30670451c47f438', 0o644),
}

def die(msg: str) -> None:
    raise SystemExit(msg)

chunks = sorted(CHUNKS.glob('chunk-*'))
if [p.name for p in chunks] != [f'chunk-{i:03d}' for i in range(20)]:
    die('expected exactly chunks 000..019')
try:
    payload = base64.b64decode(''.join(p.read_text(encoding='ascii').strip() for p in chunks), validate=True)
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
print(f'materialized {len(FILES)} Batch 38 files; payload sha256={PAYLOAD_SHA}')
