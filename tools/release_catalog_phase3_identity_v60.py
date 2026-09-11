#!/usr/bin/env python3
"""Preserve the exact Phase-3 source-local ingredient identity contract in v60.

Phase 3 reviewed semantic labels produced by ``crawl_release_catalog_v2`` and
``prepare_release_catalog_v2_assembly``.  The compact v59 release builder drops
some of that source evidence before v60 semantic enrichment runs.  This module
bridges only the release-capture call so v60 reuses the proven Phase-3 cleaning
functions instead of reimplementing or guessing their behavior.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Callable, Iterator

import crawl_release_catalog_v2 as crawl_v2
import prepare_release_catalog_v2_assembly as assembly_v2


def _text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def phase3_semantic_source_name(raw_item: dict[str, Any]) -> str:
    """Return the exact source label whose identity Phase 3 reviewed."""
    cleaned = crawl_v2._clean_ingredient(raw_item)
    if not cleaned:
        return ""
    name, _prefix_removed, _source_field = (
        assembly_v2._semantic_ingredient_name_with_source(cleaned)
    )
    return _text(name)


def _augmented_extractor(
    original_extract: Callable[[dict[str, Any]], list[dict[str, Any]]],
) -> Callable[[dict[str, Any]], list[dict[str, Any]]]:
    def extract(root: dict[str, Any]) -> list[dict[str, Any]]:
        raw_rows = root.get("ingredients") if isinstance(root, dict) else None
        if not isinstance(raw_rows, list):
            raw_rows = []
        out: list[dict[str, Any]] = []
        for raw in raw_rows:
            if not isinstance(raw, dict):
                continue
            # Let the established runtime extractor decide whether/how the line
            # is representable.  Feeding one row at a time keeps exact alignment
            # even when an invalid raw row is skipped.
            normalized = original_extract({"ingredients": [raw]})
            if not normalized:
                continue
            row = normalized[0]
            if not _text(row.get("foodKey")):
                semantic_name = phase3_semantic_source_name(raw)
                if semantic_name:
                    row["semanticSourceName"] = semantic_name
            out.append(row)
        return out

    return extract


def _augmented_compactor(
    original_compact: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    def compact(
        item: dict[str, Any],
        ingredients: dict[str, dict[str, Any]],
        *,
        source_language: str = "",
    ) -> dict[str, Any]:
        row = original_compact(
            item,
            ingredients,
            source_language=source_language,
        )
        provider_key = _text(item.get("foodKey") or item.get("key"))
        semantic_name = _text(item.get("semanticSourceName"))
        if semantic_name and not provider_key:
            row["semanticSourceName"] = semantic_name
        return row

    return compact


@contextmanager
def phase3_identity_capture(v59_module: Any) -> Iterator[None]:
    """Temporarily retain Phase-3 semantic source evidence through v59 build."""
    original_extract = v59_module.catalog.extract_recipe_ingredients
    original_compact = v59_module._compact_variant_ingredient
    v59_module.catalog.extract_recipe_ingredients = _augmented_extractor(
        original_extract
    )
    v59_module._compact_variant_ingredient = _augmented_compactor(
        original_compact
    )
    try:
        yield
    finally:
        v59_module.catalog.extract_recipe_ingredients = original_extract
        v59_module._compact_variant_ingredient = original_compact


def build_with_phase3_identity(v59_module: Any, args: Any) -> dict[str, Any]:
    """Run the v59 provider capture while preserving reviewed v60 identity input."""
    with phase3_identity_capture(v59_module):
        return v59_module.build(args)


def compact_semantic_source_name(item: dict[str, Any]) -> str:
    """Return reviewed semantic source evidence when present, else empty."""
    return _text(item.get("semanticSourceName"))
