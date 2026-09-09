#!/usr/bin/env python3
"""Build and strictly finalize the immutable Cook4Me release catalog.

The underlying scanner may produce a useful partial audit. This release entry
point is intentionally stricter: it writes the same artifact, applies optional
maintainer-reviewed canonical English overrides, and marks the snapshot complete
only when the runtime offline-catalog contract can be satisfied without guessing.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_release_catalog as scanner  # noqa: E402

DEFAULT_OUTPUT = ROOT / "custom_components" / "cook4me" / "catalog" / "release_catalog.json"
DEFAULT_OVERRIDES = ROOT / "scripts" / "catalog_canonical_overrides.json"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_overrides(path: Path) -> dict[str, dict[str, str]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"ingredients": {}, "recipes": {}}
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Cannot read canonical override file: {type(exc).__name__}") from exc
    if not isinstance(raw, dict):
        raise SystemExit("Canonical override file must contain an object")
    result: dict[str, dict[str, str]] = {"ingredients": {}, "recipes": {}}
    for section in result:
        values = raw.get(section)
        if not isinstance(values, dict):
            continue
        result[section] = {
            _text(key): _text(value)
            for key, value in values.items()
            if _text(key) and _text(value)
        }
    return result


def _apply_canonical_overrides(payload: dict[str, Any], overrides: dict[str, dict[str, str]]) -> dict[str, int]:
    counts = {"ingredients": 0, "recipes": 0}
    ingredient_overrides = overrides.get("ingredients") or {}
    for row in payload.get("ingredients") or []:
        if not isinstance(row, dict):
            continue
        identity = _text(row.get("id"))
        replacement = _text(ingredient_overrides.get(identity))
        if not replacement:
            continue
        row["canonicalName"] = replacement
        row["canonicalLanguage"] = "en"
        names = row.setdefault("names", {})
        if isinstance(names, dict):
            names["en"] = replacement
        counts["ingredients"] += 1

    recipe_overrides = overrides.get("recipes") or {}
    for row in payload.get("recipes") or []:
        if not isinstance(row, dict):
            continue
        identity = _text(row.get("id"))
        replacement = _text(recipe_overrides.get(identity))
        if not replacement:
            continue
        row["canonicalTitle"] = replacement
        row["canonicalLanguage"] = "en"
        titles = row.setdefault("titles", {})
        if isinstance(titles, dict):
            titles["en"] = replacement
        counts["recipes"] += 1
    return counts


def _strict_report(payload: dict[str, Any]) -> dict[str, Any]:
    release = payload.get("release") if isinstance(payload.get("release"), dict) else {}
    ingredients = [row for row in payload.get("ingredients") or [] if isinstance(row, dict)]
    recipes = [row for row in payload.get("recipes") or [] if isinstance(row, dict)]
    language_audit = [row for row in release.get("languageAudit") or [] if isinstance(row, dict)]

    missing_ingredient_canonical = [
        _text(row.get("id")) for row in ingredients if not _text(row.get("canonicalName"))
    ]
    missing_ingredient_nutrition = [
        _text(row.get("id"))
        for row in ingredients
        if not isinstance(row.get("nutrition"), dict) or not row.get("nutrition")
    ]
    missing_recipe_canonical = [
        _text(row.get("id")) for row in recipes if not _text(row.get("canonicalTitle"))
    ]
    missing_recipe_nutrition = [
        _text(row.get("id"))
        for row in recipes
        if not isinstance(row.get("nutrition"), dict) or not row.get("nutrition")
    ]
    failed_languages = release.get("failedLanguages") if isinstance(release.get("failedLanguages"), list) else []
    failed_details = int(release.get("failedDetailCount") or 0)
    truncated_languages = [
        _text(row.get("language")) for row in language_audit if bool(row.get("truncated"))
    ]
    expected_languages = list(release.get("sourceLanguages") or [])
    audited_languages = {_text(row.get("language")) for row in language_audit if _text(row.get("language"))}
    missing_language_audits = [
        _text(language)
        for language in expected_languages
        if _text(language) and _text(language) not in audited_languages
    ]

    complete = bool(
        ingredients
        and recipes
        and not failed_languages
        and failed_details == 0
        and not truncated_languages
        and not missing_language_audits
        and not missing_ingredient_canonical
        and not missing_ingredient_nutrition
        and not missing_recipe_canonical
        and not missing_recipe_nutrition
    )
    return {
        "complete": complete,
        "ingredientCount": len(ingredients),
        "recipeCount": len(recipes),
        "failedLanguageCount": len(failed_languages),
        "failedDetailCount": failed_details,
        "truncatedLanguages": truncated_languages,
        "missingLanguageAudits": missing_language_audits,
        "missingIngredientCanonical": missing_ingredient_canonical,
        "missingIngredientNutrition": missing_ingredient_nutrition,
        "missingRecipeCanonical": missing_recipe_canonical,
        "missingRecipeNutrition": missing_recipe_nutrition,
    }


def _scanner_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        storage_home=args.storage_home,
        token_file=args.token_file,
        output=args.output,
        release_id=args.release_id,
        app_version=args.app_version,
        max_pages=args.max_pages,
        nutrition_export=args.nutrition_export,
        fdc_api_key=args.fdc_api_key,
        fdc_delay=args.fdc_delay,
        skip_fdc=args.skip_fdc,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-home", default=str(Path.home()), help="Home containing .config/cook4me/tokens.json")
    parser.add_argument("--token-file", default="", help="Optional explicit Cook4Me token JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--release-id", default=datetime.now(timezone.utc).strftime("%Y.%m.%d-catalog1"))
    parser.add_argument("--app-version", default="36.0.0-RC3")
    parser.add_argument("--max-pages", type=int, default=1000)
    parser.add_argument("--nutrition-export", default="", help="Optional generic nutrition JSON keyed by M_FOOD_* or k:M_FOOD_*")
    parser.add_argument("--fdc-api-key", default="", help="USDA FoodData Central API key; DEMO_KEY is used when omitted")
    parser.add_argument("--fdc-delay", type=float, default=0.0, help="Delay between FDC lookups")
    parser.add_argument("--skip-fdc", action="store_true", help="Do not resolve missing ingredient nutrition online")
    parser.add_argument("--canonical-overrides", default=str(DEFAULT_OVERRIDES), help="Reviewed English canonical-name/title overrides")
    args = parser.parse_args()

    payload = scanner.build(_scanner_args(args))
    overrides = _load_overrides(Path(args.canonical_overrides).expanduser())
    applied = _apply_canonical_overrides(payload, overrides)
    report = _strict_report(payload)

    release = payload.setdefault("release", {})
    release["complete"] = bool(report["complete"])
    release["builderContract"] = "strict-release-catalog-v2"
    release["canonicalOverridesApplied"] = applied
    release["strictReport"] = report

    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(
        f"wrote {output}: complete={report['complete']} "
        f"ingredients={report['ingredientCount']} recipes={report['recipeCount']} "
        f"missing_nutrition={len(report['missingIngredientNutrition']) + len(report['missingRecipeNutrition'])} "
        f"missing_canonical={len(report['missingIngredientCanonical']) + len(report['missingRecipeCanonical'])} "
        f"failed_languages={report['failedLanguageCount']} failed_details={report['failedDetailCount']}"
    )
    if not report["complete"]:
        print("Release catalog remains disabled. Resolve strictReport findings and rebuild before committing it as a complete snapshot.")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
