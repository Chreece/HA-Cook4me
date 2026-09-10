#!/usr/bin/env python3
"""Temporary maintenance patch for keyless source-field provenance."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def patch_prep() -> None:
    path = ROOT / "tools" / "prepare_release_catalog_v2_assembly.py"
    text = path.read_text(encoding="utf-8")

    old = '''def semantic_ingredient_name(item: dict[str, Any]) -> tuple[str, bool]:
    """Recover the semantic keyless label from preserved structured evidence.

    Prefer provider food/appliance wording. If only a quantity-bearing label is
    available, remove a leading quantity and provider unit only when the same
    quantity/unit are explicitly preserved on that ingredient row. This repairs
    the old amount-in-identity capture without guessing densities or piece sizes.
    """
    source = ""
    for field in ("foodName", "applianceDescription", "applicationDescription", "cleanName"):
        source = _text(item.get(field))
        if source:
            break
    if not source:
        return "", False

    unit = item.get("unit") if isinstance(item.get("unit"), dict) else {}
    units: list[str] = []
    for field in ("name", "pluralName", "abbreviation"):
        value = _text(unit.get(field))
        if value and value not in units:
            units.append(value)

    for quantity in sorted(_quantity_forms(item.get("quantity")), key=len, reverse=True):
        for unit_name in sorted(units, key=len, reverse=True):
            pattern = (
                rf"^\\s*{re.escape(quantity)}\\s*{re.escape(unit_name)}"
                rf"(?=\\s|[-–—,:;]|$)\\s*[-–—,:;]?\\s*"
            )
            cleaned = re.sub(pattern, "", source, count=1, flags=re.IGNORECASE | re.UNICODE)
            if cleaned != source and _text(cleaned):
                return _text(cleaned), True
        pattern = rf"^\\s*{re.escape(quantity)}(?=\\s)\\s+"
        cleaned = re.sub(pattern, "", source, count=1, flags=re.IGNORECASE | re.UNICODE)
        if cleaned != source and _text(cleaned):
            return _text(cleaned), True
    return source, False
'''
    new = '''def _semantic_ingredient_name_with_source(
    item: dict[str, Any],
) -> tuple[str, bool, str]:
    """Recover semantic keyless label plus the provider field that supplied it."""
    source = ""
    source_field = ""
    for field in ("foodName", "applianceDescription", "applicationDescription", "cleanName"):
        source = _text(item.get(field))
        if source:
            source_field = field
            break
    if not source:
        return "", False, ""

    unit = item.get("unit") if isinstance(item.get("unit"), dict) else {}
    units: list[str] = []
    for field in ("name", "pluralName", "abbreviation"):
        value = _text(unit.get(field))
        if value and value not in units:
            units.append(value)

    for quantity in sorted(_quantity_forms(item.get("quantity")), key=len, reverse=True):
        for unit_name in sorted(units, key=len, reverse=True):
            pattern = (
                rf"^\\s*{re.escape(quantity)}\\s*{re.escape(unit_name)}"
                rf"(?=\\s|[-–—,:;]|$)\\s*[-–—,:;]?\\s*"
            )
            cleaned = re.sub(pattern, "", source, count=1, flags=re.IGNORECASE | re.UNICODE)
            if cleaned != source and _text(cleaned):
                return _text(cleaned), True, source_field
        pattern = rf"^\\s*{re.escape(quantity)}(?=\\s)\\s+"
        cleaned = re.sub(pattern, "", source, count=1, flags=re.IGNORECASE | re.UNICODE)
        if cleaned != source and _text(cleaned):
            return _text(cleaned), True, source_field
    return source, False, source_field


def semantic_ingredient_name(item: dict[str, Any]) -> tuple[str, bool]:
    """Recover semantic keyless label while preserving the public helper API."""
    name, changed, _source_field = _semantic_ingredient_name_with_source(item)
    return name, changed
'''
    if old not in text:
        raise SystemExit("semantic ingredient helper block not found")
    text = text.replace(old, new, 1)

    old = '''            name, changed = semantic_ingredient_name(ingredient)
            if changed:
                prefix_cleaned += 1
'''
    new = '''            name, changed, source_field = _semantic_ingredient_name_with_source(ingredient)
            if changed:
                prefix_cleaned += 1
'''
    if old not in text:
        raise SystemExit("semantic helper call not found")
    text = text.replace(old, new, 1)

    old = '''                    "occurrenceCount": 0,
                    "samples": [],
                },
            )
            row["occurrenceCount"] += 1
'''
    new = '''                    "occurrenceCount": 0,
                    "sourceFieldCounts": {},
                    "samples": [],
                },
            )
            row["occurrenceCount"] += 1
            if source_field:
                counts = row["sourceFieldCounts"]
                counts[source_field] = int(counts.get(source_field) or 0) + 1
'''
    if old not in text:
        raise SystemExit("unkeyed aggregation block not found")
    text = text.replace(old, new, 1)

    old = '''        else:
            if len(candidates) > 1:
                row["ambiguousProviderFoodKeyCandidates"] = candidates
            task_id = _task_id(
                "unkeyed_ingredient", language, row["sourceName"]
            )
            row["translationTaskId"] = task_id
            tasks.append(
                {
                    "taskId": task_id,
                    "type": "unkeyed_ingredient",
                    "sourceLanguage": language,
                    "sourceText": row["sourceName"],
                    "occurrenceCount": row["occurrenceCount"],
                    "needsTranslation": language != "en",
                    "requestedClassification": [
                        "food",
                        "equipment",
                        "other",
                        "ambiguous",
                    ],
                }
            )
'''
    new = '''        else:
            if len(candidates) > 1:
                row["ambiguousProviderFoodKeyCandidates"] = candidates
            source_fields = {
                field
                for field, count in (row.get("sourceFieldCounts") or {}).items()
                if int(count or 0) > 0
            }
            provider_food_name_only = source_fields == {"foodName"}
            if provider_food_name_only:
                row["classification"] = "food"
                row["classificationEvidence"] = "provider:foodName on every occurrence"
            if provider_food_name_only and language == "en":
                row["canonicalEnglishName"] = row["sourceName"]
                row["canonicalEnglishSource"] = "provider:english-foodName"
            else:
                task_id = _task_id(
                    "unkeyed_ingredient", language, row["sourceName"]
                )
                row["translationTaskId"] = task_id
                tasks.append(
                    {
                        "taskId": task_id,
                        "type": "unkeyed_ingredient",
                        "sourceLanguage": language,
                        "sourceText": row["sourceName"],
                        "occurrenceCount": row["occurrenceCount"],
                        "needsTranslation": language != "en",
                        "requestedClassification": (
                            ["food"]
                            if provider_food_name_only
                            else ["food", "equipment", "other", "ambiguous"]
                        ),
                        "sourceFieldCounts": dict(sorted((row.get("sourceFieldCounts") or {}).items())),
                    }
                )
'''
    if old not in text:
        raise SystemExit("unkeyed queue block not found")
    text = text.replace(old, new, 1)

    old = '''    summary = {
        "providerDetails": len(provider.get("details") or []),
'''
    new = '''    provider_food_name_only_rows = sum(
        {
            field
            for field, count in (row.get("sourceFieldCounts") or {}).items()
            if int(count or 0) > 0
        } == {"foodName"}
        for row in unkeyed_rows
    )
    provider_food_name_english_resolved = sum(
        row.get("canonicalEnglishSource") == "provider:english-foodName"
        for row in unkeyed_rows
    )
    summary = {
        "providerDetails": len(provider.get("details") or []),
'''
    if old not in text:
        raise SystemExit("summary opening not found")
    text = text.replace(old, new, 1)

    old = '''        "unkeyedExactProviderCandidatesWithSebEnglish": exact_candidates_with_english,
'''
    new = '''        "unkeyedExactProviderCandidatesWithSebEnglish": exact_candidates_with_english,
        "unkeyedProviderFoodNameOnly": provider_food_name_only_rows,
        "unkeyedProviderFoodNameEnglishResolved": provider_food_name_english_resolved,
'''
    if old not in text:
        raise SystemExit("summary exact-candidate field not found")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def patch_tests() -> None:
    test_path = ROOT / "tests" / "test_release_catalog_v2_assembly_prep.py"
    text = test_path.read_text(encoding="utf-8")
    marker = '\n    def test_wrong_marketing_food_contract_is_rejected(self):\n'
    addition = r'''
    def test_english_foodname_proves_food_semantics_without_provider_identity(self):
        provider = provider_capture()
        provider["source"]["catalogs"][0]["searchRows"] = 4
        provider["source"]["catalogs"][0]["hydratedVariants"] = 4
        provider["details"].append(
            {
                "variantId": "v4",
                "groupingFunctionalId": "g4",
                "language": "en",
                "market": "GS_GB",
                "title": "Salt test",
                "ingredients": [{"foodName": "sea salt", "cleanName": "ignored fallback"}],
            }
        )
        result, queue = prep.prepare(provider, marketing_capture())
        row = next(item for item in result["unkeyedIngredients"] if item["sourceName"] == "sea salt")
        self.assertEqual({"foodName": 1}, row["sourceFieldCounts"])
        self.assertEqual("food", row["classification"])
        self.assertEqual("provider:foodName on every occurrence", row["classificationEvidence"])
        self.assertEqual("sea salt", row["canonicalEnglishName"])
        self.assertEqual("provider:english-foodName", row["canonicalEnglishSource"])
        self.assertNotIn("providerFoodKey", row)
        self.assertFalse(any(task.get("sourceText") == "sea salt" for task in queue["tasks"]))
        self.assertEqual(1, result["summary"]["unkeyedProviderFoodNameOnly"])
        self.assertEqual(1, result["summary"]["unkeyedProviderFoodNameEnglishResolved"])

    def test_nonenglish_foodname_narrows_review_to_translation_only(self):
        provider = provider_capture()
        provider["source"]["catalogs"][0]["searchRows"] = 4
        provider["source"]["catalogs"][0]["hydratedVariants"] = 4
        provider["details"].append(
            {
                "variantId": "v4",
                "groupingFunctionalId": "g4",
                "language": "de",
                "market": "GS_DE",
                "title": "Salztest",
                "ingredients": [{"foodName": "Meersalz", "cleanName": "ignored fallback"}],
            }
        )
        result, queue = prep.prepare(provider, marketing_capture())
        row = next(item for item in result["unkeyedIngredients"] if item["sourceName"] == "Meersalz")
        self.assertEqual("food", row["classification"])
        task = next(task for task in queue["tasks"] if task.get("sourceText") == "Meersalz")
        self.assertTrue(task["needsTranslation"])
        self.assertEqual(["food"], task["requestedClassification"])
        self.assertEqual({"foodName": 1}, task["sourceFieldCounts"])
        self.assertNotIn("providerFoodKey", row)

'''
    if marker not in text:
        raise SystemExit("test insertion marker not found")
    text = text.replace(marker, "\n" + addition + marker, 1)
    test_path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_prep()
    patch_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
