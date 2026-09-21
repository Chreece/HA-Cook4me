from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "cook4me"
CATALOG = COMPONENT / "catalog" / "merged_catalog.v1.json"

sys.path.insert(0, str(COMPONENT))
from catalog_presentation import ingredient_choices  # noqa: E402


def main() -> None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    choices = ingredient_choices(catalog, "el")
    greek = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]")
    bad = [
        row for row in choices
        if not greek.search(str(row.get("name") or ""))
        or "Απροσδιόριστο" in str(row.get("name") or "")
    ]
    fragments = {"and", "or", "for serving", "and steamed eggplant", "optional"}
    visible_fragments = [
        row for row in choices
        if str(row.get("canonicalName") or "").strip().casefold() in fragments
    ]

    print(f"Greek picker choices: {len(choices)}")
    print(f"Untranslated/placeholder choices: {len(bad)}")
    print(f"Malformed fragments still visible: {len(visible_fragments)}")

    if bad:
        for row in bad[:50]:
            print(f"BAD_GREEK\t{row.get('canonicalName')}\t=>\t{row.get('name')}")
    if visible_fragments:
        for row in visible_fragments:
            print(f"BAD_FRAGMENT\t{row.get('canonicalName')}\t=>\t{row.get('name')}")
    if bad or visible_fragments:
        raise SystemExit("Greek ingredient catalog quality gate failed")


if __name__ == "__main__":
    main()
