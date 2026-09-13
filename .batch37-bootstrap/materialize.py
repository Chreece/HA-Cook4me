#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, io, pathlib, tarfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
CHUNKS = pathlib.Path(__file__).resolve().parent / 'chunks'
EXPECTED_SHA256 = '8ef26b2df0abdafa312f1a16b86d767eedaa491a3fe45e22143aa9f2073a137f'
ALLOWED = {line.strip() for line in (pathlib.Path(__file__).resolve().parent / 'paths.txt').read_text().splitlines() if line.strip()}
encoded = ''.join(p.read_text().strip() for p in sorted(CHUNKS.glob('chunk-*')))
payload = base64.b64decode(encoded, validate=True)
if hashlib.sha256(payload).hexdigest() != EXPECTED_SHA256:
    raise SystemExit('payload sha256 mismatch')
with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as tf:
    members = tf.getmembers()
    names = {m.name for m in members}
    if names != ALLOWED:
        raise SystemExit(f'payload path set mismatch: {sorted(names ^ ALLOWED)}')
    for member in members:
        p = pathlib.PurePosixPath(member.name)
        if member.isdir() or member.issym() or member.islnk() or p.is_absolute() or '..' in p.parts:
            raise SystemExit(f'unsafe payload member: {member.name}')
        is_exec = bool(member.mode & 0o111)
        if is_exec != (member.name == 'tools/classify_nutrition_review_queue_v60.py'):
            raise SystemExit(f'unexpected executable mode for {member.name}: {oct(member.mode & 0o777)}')
    tf.extractall(ROOT, filter='data')
for name in ALLOWED:
    (ROOT / name).chmod(0o755 if name == 'tools/classify_nutrition_review_queue_v60.py' else 0o644)
print(f'materialized {len(ALLOWED)} Batch 37 files; sha256={EXPECTED_SHA256}')
