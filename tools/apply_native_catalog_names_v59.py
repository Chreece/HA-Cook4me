#!/usr/bin/env python3
"""One-shot maintenance patch for provider-native catalog display names.

This script is intentionally fail-closed: every source marker must match exactly
once. It is used only to apply the reviewed v59 source change on CI and can be
removed after the resulting production files have passed their regression suite.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


def replace_region(
    text: str,
    start: str,
    end: str,
    replacement: str,
    label: str,
) -> str:
    count = text.count(start)
    if count != 1:
        raise RuntimeError(f"{label}: expected one start marker, got {count}")
    a = text.index(start)
    try:
        b = text.index(end, a + len(start))
    except ValueError as exc:
        raise RuntimeError(f"{label}: end marker missing") from exc
    return text[:a] + replacement + text[b:]


def patch_builder() -> None:
    path = "tools/build_release_catalog.py"
    text = read(path)
    text = replace_region(
        text,
        "def _compact_variant_ingredient(",
        "\ndef _compact_variant_row",
        '''def _compact_variant_ingredient(
    item: dict[str, Any],
    ingredients: dict[str, dict[str, Any]],
    *,
    source_language: str = "",
) -> dict[str, Any]:
    ident = _ingredient_id(item)
    global_row = ingredients.get(ident) or {}
    key = _text(item.get("foodKey") or item.get("key") or global_row.get("key"))
    original_name = _text(
        item.get("originalName")
        or item.get("foodName")
        or item.get("name")
        or item.get("cleanName")
    )
    original_language = _text(
        item.get("originalLanguage") or source_language
    ).lower()
    row = {
        "ingredientId": ident,
        "key": key,
        "originalName": original_name,
        "originalLanguage": original_language,
        "quantity": item.get("quantity"),
        "unit": item.get("unit"),
        "unitKey": item.get("unitKey"),
    }
    # Canonical identity lives globally. Exact provider wording lives on the
    # recipe-line reference so native users see what SEB actually published.
    if not key:
        row["canonicalName"] = _text(global_row.get("canonicalName")) or original_name
    return {
        name: value
        for name, value in row.items()
        if value not in ("", None, {}, [])
    }
''',
        "builder compact ingredient",
    )
    text = replace_once(
        text,
        '        "title",\n        "language",',
        '        "title",\n        "originalTitle",\n        "language",\n        "originalLanguage",',
        "builder compact variant fields",
    )
    text = replace_once(
        text,
        '''    for variant in variants:
        compact = [
            _compact_variant_ingredient(item, ingredients)
            for item in variant.get("ingredients") or []
            if isinstance(item, dict)
        ]''',
        '''    for variant in variants:
        variant["originalTitle"] = _text(
            variant.get("originalTitle") or variant.get("title")
        )
        variant["originalLanguage"] = _text(
            variant.get("originalLanguage")
            or variant.get("language")
            or variant.get("sourceCatalogLanguage")
        ).lower()
        compact = [
            _compact_variant_ingredient(
                item,
                ingredients,
                source_language=variant["originalLanguage"],
            )
            for item in variant.get("ingredients") or []
            if isinstance(item, dict)
        ]''',
        "builder variant native capture",
    )
    text = replace_once(
        text,
        '            "format": "normalized-ingredient-references-v1",\n            "applianceGroup":',
        '            "format": "normalized-ingredient-references-v1",\n            "providerNativeNamesStored": True,\n            "applianceGroup":',
        "builder source native-name flag",
    )
    write(path, text)


def patch_runtime() -> None:
    path = "custom_components/cook4me/release_catalog.py"
    text = read(path)
    text = replace_once(
        text,
        '''    source = _ingredient_reference(raw) or raw
    values = [_text(source.get("canonicalName") or source.get("name") or source.get("foodName"))]''',
        '''    source = _ingredient_reference(raw) or raw
    values = [
        _text(raw.get("originalName")),
        _text(source.get("canonicalName") or source.get("name") or source.get("foodName")),
    ]''',
        "runtime ingredient search",
    )
    text = replace_once(
        text,
        '        values.append(_text(variant.get("title")))',
        '        values.append(_text(variant.get("originalTitle")))\n        values.append(_text(variant.get("title")))',
        "runtime recipe search",
    )
    text = replace_region(
        text,
        "def _display_ingredient(",
        "\ndef _recipe_row",
        '''def _display_ingredient(raw: Any, language: str) -> Any:
    if not isinstance(raw, dict):
        return deepcopy(raw)
    source = _ingredient_reference(raw) or raw
    requested_language = _language(language)
    original_name = _text(raw.get("originalName"))
    original_language = _language(raw.get("originalLanguage"))
    translated_name = _translated_name(source, language) or _translated_name(raw, language)
    name = (
        original_name
        if original_name and original_language == requested_language
        else translated_name or original_name
    )
    ident = _text(
        raw.get("ingredientId")
        or raw.get("id")
        or source.get("id")
        or source.get("ingredientId")
        or raw.get("key")
        or source.get("key")
    )
    key = _text(
        raw.get("key")
        or raw.get("foodKey")
        or source.get("key")
        or source.get("foodKey")
    )
    row: dict[str, Any] = {}
    if ident:
        row["ingredientId"] = ident
    if key:
        row["key"] = key
        row["foodKey"] = key
    if name:
        row["name"] = name
        row["foodName"] = name
    if original_name:
        row["originalName"] = original_name
    if original_language:
        row["originalLanguage"] = original_language
    canonical = _text(source.get("canonicalName") or raw.get("canonicalName"))
    if canonical:
        row["canonicalName"] = canonical
    for field in ("quantity", "unit", "unitKey", "functionalId"):
        if raw.get(field) not in (None, ""):
            row[field] = deepcopy(raw[field])
    return row
''',
        "runtime display ingredient",
    )
    text = replace_once(
        text,
        '''    title = _text(display.get("title")) or _text(recipe.get("canonicalName"))
    row: dict[str, Any] = {''',
        '''    original_title = _text(display.get("originalTitle") or display.get("title"))
    original_language = _language(
        display.get("originalLanguage") or display.get("language")
    )
    requested_language = _language(language)
    fallback_title = _text(display.get("title")) or _text(recipe.get("canonicalName"))
    title = (
        original_title
        if original_title and original_language == requested_language
        else fallback_title or original_title
    )
    row: dict[str, Any] = {''',
        "runtime recipe native title selection",
    )
    text = replace_once(
        text,
        '        "title": title or None,\n        "canonicalName":',
        '        "title": title or None,\n        "originalTitle": original_title or None,\n        "originalLanguage": original_language or None,\n        "canonicalName":',
        "runtime expose original recipe fields",
    )
    text = replace_once(
        text,
        '''                    "groupingFunctionalId": variant.get("groupingFunctionalId"),
                    "language": variant.get("language"),''',
        '''                    "groupingFunctionalId": variant.get("groupingFunctionalId"),
                    "title": variant.get("title"),
                    "originalTitle": variant.get("originalTitle") or variant.get("title"),
                    "language": variant.get("language"),
                    "originalLanguage": variant.get("originalLanguage") or variant.get("language"),''',
        "runtime variant native metadata",
    )
    write(path, text)


def patch_prep() -> None:
    path = "tools/prepare_release_catalog_v2_assembly.py"
    text = read(path)
    text = replace_region(
        text,
        '    groups: dict[str, dict[str, Any]] = {}',
        '    title_tasks: dict[str, dict[str, Any]] = {}',
        '''    groups: dict[str, dict[str, Any]] = {}
    title_task_users: dict[tuple[str, str], list[str]] = defaultdict(list)
    for detail in provider.get("details") or []:
        grouping_id = _text(
            detail.get("groupingFunctionalId")
            or detail.get("topRecipeId")
            or detail.get("recipeFunctionalId")
            or detail.get("variantId")
        )
        if not grouping_id:
            continue
        language = _text(detail.get("language")).lower()
        market = _text(detail.get("market"))
        title = _text(detail.get("title") or detail.get("normalizedTitle"))
        variant_id = _text(detail.get("variantId"))
        row = groups.get(grouping_id)
        if row is None:
            row = {
                "groupingFunctionalId": grouping_id,
                # Legacy representative fields remain for review-tool compatibility.
                "language": language,
                "market": market,
                "title": title,
                "variantIds": [],
                "originalTitles": [],
            }
            groups[grouping_id] = row
        row["variantIds"].append(variant_id)
        if title:
            row["originalTitles"].append(
                {
                    "variantId": variant_id,
                    "language": language,
                    "market": market,
                    "name": title,
                }
            )
            if language == "en" and not row.get("canonicalEnglishTitle"):
                row["canonicalEnglishTitle"] = title
                row["canonicalEnglishSource"] = "seb:en-sibling"

    # Only groups without an official English sibling need semantic review.
    for grouping_id, row in groups.items():
        if row.get("canonicalEnglishTitle"):
            continue
        language = _text(row.get("language")).lower()
        title = _text(row.get("title"))
        if title:
            title_task_users[(language, _norm(title))].append(grouping_id)

''',
        "prep retain sibling originals",
    )
    text = replace_once(
        text,
        '''    for group in group_rows:
        group["variantIds"] = sorted(set(group["variantIds"]))
        group["variantCount"] = len(group["variantIds"])''',
        '''    for group in group_rows:
        group["variantIds"] = sorted(set(group["variantIds"]))
        unique_originals = {}
        for original in group.get("originalTitles") or []:
            if not isinstance(original, dict):
                continue
            identity = (
                _text(original.get("variantId")),
                _text(original.get("language")).lower(),
                _text(original.get("market")),
                _text(original.get("name")),
            )
            unique_originals.setdefault(identity, original)
        group["originalTitles"] = sorted(
            unique_originals.values(),
            key=lambda value: (
                _text(value.get("language")),
                _text(value.get("market")),
                _text(value.get("variantId")),
                _text(value.get("name")).casefold(),
            ),
        )
        group["variantCount"] = len(group["variantIds"])''',
        "prep dedupe original titles",
    )
    text = replace_once(
        text,
        '        "providerRecipeGroups": len(group_rows),\n        "providerFoodCatalogKeys":',
        '        "providerRecipeGroups": len(group_rows),\n        "recipeGroupsWithMultipleOriginalTitles": sum(\n            len(row.get("originalTitles") or []) > 1 for row in group_rows\n        ),\n        "providerFoodCatalogKeys":',
        "prep native-title summary",
    )
    text = replace_once(
        text,
        '            "translationNeverMergesRecipeGroups": True,\n            "unkeyedCrossLanguageMergeFromTranslation": False,',
        '            "translationNeverMergesRecipeGroups": True,\n            "providerNativeTitlesPreserved": True,\n            "unkeyedCrossLanguageMergeFromTranslation": False,',
        "prep native-title identity policy",
    )
    write(path, text)


def patch_frontend() -> None:
    path = "custom_components/cook4me/frontend/cook4me-panel-v59.js"
    text = read(path)
    text = replace_once(
        text,
        '"title","canonicalName","cover","language","market"',
        '"title","originalTitle","originalLanguage","canonicalName","cover","language","market"',
        "frontend compact shell native metadata",
    )
    write(path, text)


def main() -> int:
    patch_builder()
    patch_runtime()
    patch_prep()
    patch_frontend()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
