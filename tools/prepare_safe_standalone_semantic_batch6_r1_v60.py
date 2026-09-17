#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "tools/apply_safe_standalone_semantic_batch6_v60.py"
SOURCE_ID = "local:uk:3a54c3b6158ad1e7b926"

text = HELPER.read_text(encoding="utf-8")
needle = f'"sourceIngredientId": "{SOURCE_ID}"'
pos = text.find(needle)
if pos < 0:
    raise RuntimeError("batch-6 equivalence-root parsley decision was not found")
start = text.rfind("    {\n", 0, pos)
end = text.find("    },\n", pos)
if start < 0 or end < 0:
    raise RuntimeError("could not isolate batch-6 parsley decision block")
end += len("    },\n")
text = text[:start] + text[end:]
if text.count(SOURCE_ID) != 0:
    raise RuntimeError("equivalence-root parsley source still appears in batch-6 helper")
old = '    if len(DECISIONS) != 10:\n        raise RuntimeError(f"expected ten decisions, got {len(DECISIONS)}")\n'
new = '    if len(DECISIONS) != 9:\n        raise RuntimeError(f"expected nine decisions, got {len(DECISIONS)}")\n'
if text.count(old) != 1:
    raise RuntimeError("batch-6 decision-count guard anchor drift")
text = text.replace(old, new, 1)
HELPER.write_text(text, encoding="utf-8")
print("prepared batch 6 r1 with 9 decisions; preserved standalone equivalence root", SOURCE_ID)
