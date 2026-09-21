from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "custom_components" / "cook4me" / "catalog" / "merged_catalog.v1.json"
LOCALE = ROOT / "custom_components" / "cook4me" / "catalog_ui_locales" / "el.json"


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join("".join(ch for ch in text if not unicodedata.combining(ch)).split())


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

    canonical_usage = Counter()
    examples = defaultdict(list)
    missing = []
    for ident, count in usage.items():
        row = by_id.get(ident)
        if not row:
            continue
        canonical = str(row.get("canonicalName") or row.get("name") or "").strip()
        if not canonical:
            continue
        canonical_usage[canonical] += count
        label = labels.get(norm(canonical), "")
        if not label:
            missing.append((count, canonical))
        if len(examples[canonical]) < 3:
            examples[canonical].append(ident)

    greek = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
    latin = re.compile(r"[A-Za-z]")
    undefined = []
    latin_rows = []
    for key, value in labels.items():
        if "Απροσδιόριστο" in value or "μη προσδιορισ" in value.casefold():
            undefined.append((canonical_usage.get(key, 0), key, value))
        if latin.search(value):
            latin_rows.append((canonical_usage.get(key, 0), key, value))

    print(f"Greek labels: {len(labels)}")
    print(f"Catalog ingredients: {len(ingredients)}")
    print(f"Used ingredient identities: {len(usage)}")
    print(f"Used canonical names: {len(canonical_usage)}")
    print(f"Used canonicals without Greek override: {len(missing)}")
    print(f"Undefined-style Greek labels: {len(undefined)}")
    print(f"Labels with Latin characters: {len(latin_rows)}")
    print("\nTOP_USED_GREEK_LABELS")
    for canonical, count in canonical_usage.most_common(240):
        label = labels.get(norm(canonical), "")
        print(f"{count:6d}\t{canonical}\t=>\t{label}")
    print("\nUNDEFINED_LABELS")
    for count, key, value in sorted(undefined, reverse=True):
        print(f"{count:6d}\t{key}\t=>\t{value}")
    print("\nMISSING_USED")
    for count, canonical in sorted(missing, reverse=True)[:120]:
        print(f"{count:6d}\t{canonical}")
    print("\nLATIN_IN_GREEK")
    for count, key, value in sorted(latin_rows, reverse=True)[:120]:
        print(f"{count:6d}\t{key}\t=>\t{value}")


if __name__ == "__main__":
    main()
