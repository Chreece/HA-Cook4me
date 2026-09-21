from __future__ import annotations

from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
CATALOG = COMPONENT / "catalog" / "merged_catalog.v1.json"
LOCALE = COMPONENT / "catalog_ui_locales" / "el.json"

sys.path.insert(0, str(COMPONENT))
from catalog_presentation import clean_name, display_name, name_key  # noqa: E402


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    locale = json.loads(LOCALE.read_text(encoding="utf-8"))
    labels = locale.get("labels") or {}
    ingredients = [row for row in catalog.get("ingredients") or [] if isinstance(row, dict)]
    by_id = {}
    for row in ingredients:
        for key in ("id", "ingredientId", "key", "foodKey"):
            value = str(row.get(key) or "").strip()
            if value:
                by_id.setdefault(value, row)

    usage = Counter()
    for recipe in catalog.get("recipes") or []:
        if not isinstance(recipe, dict):
            continue
        for variant in recipe.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            for raw in variant.get("ingredients") or []:
                if not isinstance(raw, dict):
                    continue
                ident = str(raw.get("ingredientId") or raw.get("id") or raw.get("key") or raw.get("foodKey") or "").strip()
                if ident:
                    usage[ident] += 1

    key_usage = Counter()
    representative = {}
    for ident, count in usage.items():
        row = by_id.get(ident)
        if not row:
            continue
        canonical = clean_name(row.get("canonicalName") or row.get("name") or "")
        key = name_key(canonical)
        if not key:
            continue
        key_usage[key] += count
        representative.setdefault(key, row)

    greek = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
    latin = re.compile(r"[A-Za-z]")
    fallback_english = []
    no_greek = []
    actual = []
    overlay_used = 0
    raw_translation_used = 0
    for key, count in key_usage.items():
        row = representative[key]
        canonical = clean_name(row.get("canonicalName") or row.get("name") or "")
        shown = display_name(row, "el")
        source_translation = str((row.get("translations") or {}).get("el") or "").strip()
        if key in labels:
            source = "overlay"
            overlay_used += 1
        elif source_translation:
            source = "catalog-el"
            raw_translation_used += 1
        else:
            source = "canonical-fallback"
        actual.append((count, key, canonical, shown, source))
        if not greek.search(shown):
            no_greek.append((count, key, canonical, shown, source))
        if source == "canonical-fallback":
            fallback_english.append((count, key, canonical, shown, source))

    undefined = [
        (key_usage.get(key, 0), key, value)
        for key, value in labels.items()
        if "Απροσδιόριστο" in value or "μη προσδιορισ" in value.casefold()
    ]
    latin_rows = [
        (key_usage.get(key, 0), key, value)
        for key, value in labels.items()
        if latin.search(value)
    ]

    print(f"Greek overlay labels: {len(labels)}")
    print(f"Catalog ingredients: {len(ingredients)}")
    print(f"Used ingredient identities: {len(usage)}")
    print(f"Used presentation keys: {len(key_usage)}")
    print(f"Used keys served by Greek overlay: {overlay_used}")
    print(f"Used keys served by catalog Greek translation: {raw_translation_used}")
    print(f"Used keys falling back to canonical/non-Greek: {len(fallback_english)}")
    print(f"Actually displayed non-Greek names: {len(no_greek)}")
    print(f"Undefined-style Greek overlay labels: {len(undefined)}")
    print(f"Overlay labels with Latin characters: {len(latin_rows)}")

    print("\nTOP_USED_ACTUAL_GREEK_LABELS")
    for count, key, canonical, shown, source in sorted(actual, reverse=True)[:280]:
        print(f"{count:6d}\t{canonical}\t=>\t{shown}\t[{source}]")

    print("\nCANONICAL_FALLBACKS")
    for row in sorted(fallback_english, reverse=True)[:220]:
        count, key, canonical, shown, source = row
        print(f"{count:6d}\t{canonical}\t=>\t{shown}")

    print("\nNON_GREEK_DISPLAY")
    for row in sorted(no_greek, reverse=True)[:220]:
        count, key, canonical, shown, source = row
        print(f"{count:6d}\t{canonical}\t=>\t{shown}\t[{source}]")

    print("\nUNDEFINED_LABELS")
    for count, key, value in sorted(undefined, reverse=True):
        print(f"{count:6d}\t{key}\t=>\t{value}")

    print("\nLATIN_IN_GREEK_OVERLAY")
    for count, key, value in sorted(latin_rows, reverse=True)[:120]:
        print(f"{count:6d}\t{key}\t=>\t{value}")


if __name__ == "__main__":
    main()
