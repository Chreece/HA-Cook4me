#!/usr/bin/env python3
"""Canonical v60 release-pipeline entry point with exact review overlays enabled."""
from __future__ import annotations

import json

import build_release_catalog_v60_reviewed as reviewed_builder
import run_release_catalog_v60_pipeline as pipeline


def run_pipeline(args, **kwargs):
    """Run the proven one-capture state machine using the reviewed capture facade."""
    kwargs.setdefault("build_func", reviewed_builder.build)
    kwargs.setdefault("finalize_func", reviewed_builder.apply_reviewed_nutrition)
    return pipeline.run_pipeline(args, **kwargs)


def main() -> int:
    args = pipeline._parser().parse_args()
    manifest = run_pipeline(args)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest.get("readyForActivation") else 2


if __name__ == "__main__":
    raise SystemExit(main())
