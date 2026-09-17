#!/usr/bin/env python3
"""Run the one-shot high-confidence alias patch with precise guarded edits."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "tools/patch_high_confidence_syntax_aliases_v60.py"
AGGREGATE_TEST = ROOT / "tests/test_compile_release_catalog_semantics_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_high_alias_patcher", PATCHER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

_original = mod.replace_once


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if label == "identity high alias receipt" and count == 2:
        before, marker, after = text.rpartition(old)
        if not marker:
            raise RuntimeError("identity high alias receipt anchor disappeared")
        return before + new + after
    if label == "alias map insertion":
        new = new.replace(
            'int(summary.get("excludedConflictGroupCount") or -1)',
            'int(summary.get("excludedConflictGroupCount", -1))',
        )
    return _original(text, old, new, label)


def _patch_aggregate_test() -> None:
    text = AGGREGATE_TEST.read_text(encoding="utf-8")
    old = '''        standalone_equivalence_count = len(\n            standalone_equivalences.get("items") or []\n        )\n        review_total = total + standalone_count + standalone_equivalence_count\n'''
    new = '''        standalone_equivalence_count = len(\n            standalone_equivalences.get("items") or []\n        )\n        high_confidence_syntax_aliases = (\n            mod._load_high_confidence_syntax_alias_payload(\n                tools / "release_catalog_semantic_high_confidence_syntax_aliases.v1.json"\n            )\n        )\n        high_confidence_syntax_alias_count = len(\n            high_confidence_syntax_aliases.get("items") or []\n        )\n        review_total = total + standalone_count + standalone_equivalence_count\n'''
    if text.count(old) != 1:
        raise RuntimeError("aggregate semantic alias-count insertion anchor drift")
    text = text.replace(old, new, 1)

    old = '''            total + standalone_equivalence_count,\n'''
    new = '''            total\n            + standalone_equivalence_count\n            + high_confidence_syntax_alias_count,\n'''
    if text.count(old) != 1:
        raise RuntimeError("aggregate semantic concept-delta assertion anchor drift")
    text = text.replace(old, new, 1)

    marker = '''        self.assertEqual(confirmed["summary"]["confirmedSourceLabels"], total)\n'''
    addition = '''        self.assertEqual(confirmed["summary"]["confirmedSourceLabels"], total)\n        self.assertEqual(\n            confirmed["summary"]["highConfidenceSyntaxAliasConcepts"],\n            high_confidence_syntax_alias_count,\n        )\n'''
    if text.count(marker) != 1:
        raise RuntimeError("aggregate semantic alias-summary assertion anchor drift")
    text = text.replace(marker, addition, 1)
    AGGREGATE_TEST.write_text(text, encoding="utf-8")


mod.replace_once = _replace_once
result = mod.main()
_patch_aggregate_test()
raise SystemExit(result)
