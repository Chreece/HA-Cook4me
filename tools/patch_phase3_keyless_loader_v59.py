#!/usr/bin/env python3
"""Temporary maintenance patch for Phase 3 keyless review batching."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def patch_loader() -> None:
    path = ROOT / "tools" / "apply_release_catalog_reviews_v2.py"
    text = path.read_text(encoding="utf-8")

    old = '''def _keyless_reviews() -> dict[tuple[str, str], dict[str, Any]]:
    value = json.loads(KEYLESS_REVIEW.read_text(encoding="utf-8"))
    if value.get("kind") != "cook4me-reviewed-keyless-ingredient-semantics":
        raise RuntimeError("invalid keyless ingredient review file")
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in value.get("items") or []:
        if not isinstance(row, dict):
            continue
        language = _text(row.get("language")).lower()
        source = _text(row.get("source"))
        english = _text(row.get("english"))
        classification = _text(row.get("classification")).lower()
        if not language or not source or not english or classification not in {"food", "equipment", "other"}:
            continue
        key = (language, _norm(source))
        if key in out and out[key] != row:
            raise RuntimeError(f"conflicting keyless review for {language}/{source}")
        out[key] = row
    return out
'''

    new = '''def _keyless_review_paths() -> list[Path]:
    extras = sorted(
        path
        for path in (ROOT / "tools").glob("release_catalog_reviewed_keyless_ingredients_*.v1.json")
        if path != KEYLESS_REVIEW
    )
    return [KEYLESS_REVIEW, *extras]


def _keyless_reviews() -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for path in _keyless_review_paths():
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("kind") != "cook4me-reviewed-keyless-ingredient-semantics":
            raise RuntimeError(f"invalid keyless ingredient review file: {path.name}")
        for row in value.get("items") or []:
            if not isinstance(row, dict):
                continue
            language = _text(row.get("language")).lower()
            source = _text(row.get("source"))
            english = _text(row.get("english"))
            classification = _text(row.get("classification")).lower()
            if not language or not source or not english or classification not in {"food", "equipment", "other"}:
                continue
            key = (language, _norm(source))
            existing = out.get(key)
            if existing:
                if (
                    _norm(existing.get("english")) != _norm(english)
                    or _text(existing.get("classification")).lower() != classification
                ):
                    raise RuntimeError(
                        f"conflicting keyless review for {language}/{source}: "
                        f"{existing.get('english')!r}/{existing.get('classification')!r} vs "
                        f"{english!r}/{classification!r}"
                    )
                continue
            normalized = dict(row)
            normalized["language"] = language
            normalized["source"] = source
            normalized["english"] = english
            normalized["classification"] = classification
            normalized["reviewFile"] = path.name
            out[key] = normalized
    return out
'''
    if old not in text:
        raise SystemExit("keyless review loader block not found")
    text = text.replace(old, new, 1)

    old = '''            row["reviewConfidence"] = review.get("confidence") or "reviewed"
            row["reviewed"] = True
'''
    new = '''            row["reviewConfidence"] = review.get("confidence") or "reviewed"
            row["keylessSemanticReviewFile"] = _text(review.get("reviewFile")) or KEYLESS_REVIEW.name
            row["reviewed"] = True
'''
    if old not in text:
        raise SystemExit("keyless application block not found")
    text = text.replace(old, new, 1)

    old = '''    recipe_review_files = [path.name for path in _recipe_title_review_paths()]
    queue["reviewOverlay"] = {
        "providerFoodEnglish": FOOD_REVIEW.name,
        "keylessIngredientSemantics": KEYLESS_REVIEW.name,
        "entryMealEnglish": ENTRY_MEAL_REVIEW.name,
        "recipeTitleEnglish": RECIPE_TITLE_REVIEW.name,
        "recipeTitleEnglishFiles": recipe_review_files,
        "removedTaskCount": len(remove_tasks),
    }
'''
    new = '''    recipe_review_files = [path.name for path in _recipe_title_review_paths()]
    keyless_review_files = [path.name for path in _keyless_review_paths()]
    queue["reviewOverlay"] = {
        "providerFoodEnglish": FOOD_REVIEW.name,
        "keylessIngredientSemantics": KEYLESS_REVIEW.name,
        "keylessIngredientSemanticFiles": keyless_review_files,
        "entryMealEnglish": ENTRY_MEAL_REVIEW.name,
        "recipeTitleEnglish": RECIPE_TITLE_REVIEW.name,
        "recipeTitleEnglishFiles": recipe_review_files,
        "removedTaskCount": len(remove_tasks),
    }
'''
    if old not in text:
        raise SystemExit("review overlay block not found")
    text = text.replace(old, new, 1)

    old = '''    summary["reviewedKeylessIngredientSemanticsApplied"] = keyless_review_applied
    summary["reviewedRecipeTitleEnglishApplied"] = recipe_title_review_applied
'''
    new = '''    summary["reviewedKeylessIngredientSemanticsApplied"] = keyless_review_applied
    summary["reviewedKeylessIngredientSemanticFiles"] = keyless_review_files
    summary["reviewedRecipeTitleEnglishApplied"] = recipe_title_review_applied
'''
    if old not in text:
        raise SystemExit("summary block not found")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def patch_tests() -> None:
    test_path = ROOT / "tests" / "test_release_catalog_review_overlay.py"
    text = test_path.read_text(encoding="utf-8")
    marker = '\n\nif __name__ == "__main__":\n    unittest.main()\n'
    addition = r'''

    def test_numbered_keyless_review_file_is_loaded_with_provenance(self):
        review_path = ROOT / "tools" / "release_catalog_reviewed_keyless_ingredients_zz_01.v1.json"
        review_path.write_text(
            '{"schemaVersion":1,"kind":"cook4me-reviewed-keyless-ingredient-semantics",'
            '"items":[{"language":"zz","source":"Proof food","english":"Proof food",'
            '"classification":"food","confidence":"high"}]}\n',
            encoding="utf-8",
        )
        try:
            reviews = overlay._keyless_reviews()
            row = reviews[("zz", overlay._norm("Proof food"))]
            self.assertEqual("Proof food", row["english"])
            self.assertEqual("food", row["classification"])
            self.assertEqual(review_path.name, row["reviewFile"])
        finally:
            review_path.unlink(missing_ok=True)

    def test_conflicting_numbered_keyless_reviews_fail_closed(self):
        first = ROOT / "tools" / "release_catalog_reviewed_keyless_ingredients_zz_01.v1.json"
        second = ROOT / "tools" / "release_catalog_reviewed_keyless_ingredients_zz_02.v1.json"
        first.write_text(
            '{"schemaVersion":1,"kind":"cook4me-reviewed-keyless-ingredient-semantics",'
            '"items":[{"language":"zz","source":"Ambiguous","english":"Cream",'
            '"classification":"food","confidence":"high"}]}\n',
            encoding="utf-8",
        )
        second.write_text(
            '{"schemaVersion":1,"kind":"cook4me-reviewed-keyless-ingredient-semantics",'
            '"items":[{"language":"zz","source":"Ambiguous","english":"Cream",'
            '"classification":"equipment","confidence":"high"}]}\n',
            encoding="utf-8",
        )
        try:
            with self.assertRaisesRegex(RuntimeError, "conflicting keyless review"):
                overlay._keyless_reviews()
        finally:
            first.unlink(missing_ok=True)
            second.unlink(missing_ok=True)
'''
    if marker not in text:
        raise SystemExit("unittest footer not found")
    text = text.replace(marker, addition + marker, 1)
    test_path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_loader()
    patch_tests()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
