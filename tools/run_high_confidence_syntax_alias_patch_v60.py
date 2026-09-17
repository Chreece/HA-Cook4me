#!/usr/bin/env python3
"""Run the one-shot high-confidence alias patch with one disambiguated anchor."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "tools/patch_high_confidence_syntax_aliases_v60.py"
spec = importlib.util.spec_from_file_location("cook4me_high_alias_patcher", PATCHER)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

_original = mod.replace_once


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if label == "identity high alias receipt" and count == 2:
        # The compiler has one standalone-disposition branch in concept-policy
        # selection and one in source-identity receipt emission. This patch must
        # target only the latter, which is the second occurrence.
        before, marker, after = text.rpartition(old)
        if not marker:
            raise RuntimeError("identity high alias receipt anchor disappeared")
        return before + new + after
    return _original(text, old, new, label)


mod.replace_once = _replace_once
raise SystemExit(mod.main())
