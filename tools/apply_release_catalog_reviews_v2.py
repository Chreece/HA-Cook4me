#!/usr/bin/env python3
"""Apply reviewed canonical-English/keyless semantics to offline assembly prep.

This is a deterministic local maintenance transform. It consumes the output of
``prepare_release_catalog_v2_assembly.py`` and removes translation/classification
tasks that have already been reviewed in versioned repo evidence files.
Provider recipe/ingredient identities are never changed, and a keyless label is
never promoted to an M_FOOD provider identity.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FOOD_REVIEW = ROOT / "tools" / "release_catalog_reviewed_provider_food_english.v2.json"
KEYLESS_REVIEW = ROOT / "tools" / "release_catalog_reviewed_keyless_ingredients.v1.json"
RECIPE_TITLE_REVIEW = ROOT / "tools" / "release_catalog_reviewed_recipe_titles.v1.json"


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", _text(value))).casefold()


def _load_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: expected JSON object")
    return value


def _food_reviews() -> dict[str, dict[str, Any]]:
    value = json.loads(FOOD_REVIEW.read_text(encoding="utf-8"))
    if value.get("kind") != "cook4me-reviewed-provider-food-english":
        raise RuntimeError("invalid provider-food English review file")
    return {
        str(key): row
        for key, row in (value.get("items") or {}).items()
        if isinstance(row, dict) and _text(row.get("english"))
    }


def _keyless_reviews() -> dict[tuple[str, str], dict[str, Any]]:
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


def _recipe_title_reviews() -> dict[tuple[str, str], dict[str, Any]]:
    value = json.loads(RECIPE_TITLE_REVIEW.read_text(encoding="utf-8"))
    if value.get("kind") != "cook4me-reviewed-recipe-title-english":
        raise RuntimeError("invalid reviewed recipe-title English file")
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for row in value.get("items") or []:
        if not isinstance(row, dict):
            continue
        language = _text(row.get("language")).lower()
        source = _text(row.get("source"))
        english = _text(row.get("english"))
        confidence = _text(row.get("confidence")).lower() or "reviewed"
        if not language or not source or not english:
            continue
        key = (language, _norm(source))
        if key in out:
            existing = out[key]
            if _norm(existing.get("english")) != _norm(english):
                raise RuntimeError(
                    f"conflicting recipe-title review for {language}/{source}: "
                    f"{existing.get('english')!r} vs {english!r}"
                )
            continue
        normalized = dict(row)
        normalized["language"] = language
        normalized["source"] = source
        normalized["english"] = english
        normalized["confidence"] = confidence
        out[key] = normalized
    return out


def apply_reviews(prep: dict[str, Any], queue: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if prep.get("kind") != "cook4me-release-assembly-prep":
        raise RuntimeError("expected cook4me-release-assembly-prep")
    if queue.get("kind") != "cook4me-local-translation-queue":
        raise RuntimeError("expected cook4me-local-translation-queue")

    food_reviews = _food_reviews()
    keyless_reviews = _keyless_reviews()
    recipe_title_reviews = _recipe_title_reviews()
    remove_tasks: set[str] = set()
    provider_review_applied = 0
    keyless_review_applied = 0
    recipe_title_review_applied = 0

    provider_foods = prep.get("providerFoods") or []
    provider_by_key = {
        _text(row.get("key")): row
        for row in provider_foods
        if isinstance(row, dict) and _text(row.get("key"))
    }
    for key, review in food_reviews.items():
        row = provider_by_key.get(key)
        if not row:
            continue
        existing = _text(row.get("canonicalEnglishName"))
        reviewed = _text(review.get("english"))
        if existing and _norm(existing) != _norm(reviewed):
            raise RuntimeError(
                f"reviewed provider English conflicts with SEB English for {key}: {existing!r} vs {reviewed!r}"
            )
        if not existing:
            row["canonicalEnglishName"] = reviewed
            row["canonicalEnglishSource"] = "reviewed:provider-food-english-v2"
            row["canonicalEnglishConfidence"] = review.get("confidence") or "reviewed"
            if review.get("notes"):
                row["canonicalEnglishNotes"] = review["notes"]
            provider_review_applied += 1
        task_id = _text(row.pop("translationTaskId", ""))
        if task_id:
            remove_tasks.add(task_id)

    # Recipe-title reviews change labels only. Grouping/variant IDs and every
    # provider-native title remain untouched.
    for row in prep.get("recipeGroups") or []:
        if not isinstance(row, dict):
            continue
        task_id = _text(row.get("translationTaskId"))
        if not task_id:
            continue
        language = _text(row.get("language")).lower()
        source = _text(row.get("title"))
        review = recipe_title_reviews.get((language, _norm(source)))
        if not review:
            continue
        reviewed = _text(review.get("english"))
        existing = _text(row.get("canonicalEnglishTitle"))
        if existing and _norm(existing) != _norm(reviewed):
            raise RuntimeError(
                f"recipe-title review conflicts with existing English for "
                f"{language}/{source}: {existing!r} vs {reviewed!r}"
            )
        row["canonicalEnglishTitle"] = reviewed
        row["canonicalEnglishSource"] = "reviewed:recipe-title-v1"
        row["canonicalEnglishConfidence"] = review.get("confidence") or "reviewed"
        if review.get("notes"):
            row["canonicalEnglishNotes"] = review["notes"]
        row.pop("translationTaskId", None)
        remove_tasks.add(task_id)
        recipe_title_review_applied += 1

    for row in prep.get("unkeyedIngredients") or []:
        if not isinstance(row, dict):
            continue
        language = _text(row.get("sourceLanguage")).lower()
        source = _text(row.get("sourceName"))
        review = keyless_reviews.get((language, _norm(source)))
        if review:
            english = _text(review.get("english"))
            existing = _text(row.get("canonicalEnglishName"))
            if existing and _norm(existing) != _norm(english):
                raise RuntimeError(
                    f"keyless review conflicts with existing English for {language}/{source}: {existing!r} vs {english!r}"
                )
            row["canonicalEnglishName"] = english
            row["canonicalEnglishSource"] = "reviewed:keyless-ingredient-v1"
            row["classification"] = review["classification"]
            row["reviewConfidence"] = review.get("confidence") or "reviewed"
            row["reviewed"] = True
            task_id = _text(row.pop("translationTaskId", ""))
            if task_id:
                remove_tasks.add(task_id)
            keyless_review_applied += 1
            continue

        # An exact SEB-name candidate may depend on a provider food whose English
        # label was supplied by the reviewed provider-food table rather than GB.
        candidate = _text(row.get("exactProviderFoodKeyCandidate"))
        provider_food = provider_by_key.get(candidate)
        if candidate and provider_food and not _text(row.get("canonicalEnglishName")):
            english = _text(provider_food.get("canonicalEnglishName"))
            if english:
                row["canonicalEnglishName"] = english
                row["canonicalEnglishSource"] = "reviewed:provider-food-exact-label-candidate"

    remaining = [
        row
        for row in queue.get("tasks") or []
        if isinstance(row, dict) and _text(row.get("taskId")) not in remove_tasks
    ]
    queue["tasks"] = remaining
    queue["schemaVersion"] = max(4, int(queue.get("schemaVersion") or 0))
    queue["reviewOverlay"] = {
        "providerFoodEnglish": "release_catalog_reviewed_provider_food_english.v2.json",
        "keylessIngredientSemantics": "release_catalog_reviewed_keyless_ingredients.v1.json",
        "recipeTitleEnglish": "release_catalog_reviewed_recipe_titles.v1.json",
        "removedTaskCount": len(remove_tasks),
    }
    queue["summary"] = {
        "taskCount": len(remaining),
        "providerFoodEnglish": sum(row.get("type") == "provider_food_english" for row in remaining),
        "recipeTitleEnglish": sum(row.get("type") == "recipe_title_english" for row in remaining),
        "unkeyedIngredient": sum(row.get("type") == "unkeyed_ingredient" for row in remaining),
    }

    summary = prep.setdefault("summary", {})
    summary["reviewedProviderFoodEnglishApplied"] = provider_review_applied
    summary["reviewedKeylessIngredientSemanticsApplied"] = keyless_review_applied
    summary["reviewedRecipeTitleEnglishApplied"] = recipe_title_review_applied
    summary["providerFoodsCanonicalEnglishResolved"] = sum(
        bool(_text(row.get("canonicalEnglishName"))) for row in provider_foods if isinstance(row, dict)
    )
    summary["usedProviderFoodsCanonicalEnglishResolved"] = sum(
        bool(row.get("usedByRecipe")) and bool(_text(row.get("canonicalEnglishName")))
        for row in provider_foods if isinstance(row, dict)
    )
    summary["recipeGroupsCanonicalEnglishResolved"] = sum(
        bool(_text(row.get("canonicalEnglishTitle")))
        for row in prep.get("recipeGroups") or []
        if isinstance(row, dict)
    )
    summary["translationTasksRemaining"] = len(remaining)
    summary["providerFoodTranslationTasksRemaining"] = queue["summary"]["providerFoodEnglish"]
    summary["recipeTitleTranslationTasksRemaining"] = queue["summary"]["recipeTitleEnglish"]
    summary["unkeyedIngredientTasksRemaining"] = queue["summary"]["unkeyedIngredient"]
    prep["reviewOverlay"] = queue["reviewOverlay"]
    prep["schemaVersion"] = max(4, int(prep.get("schemaVersion") or 0))
    return prep, queue


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prep", required=True)
    parser.add_argument("--queue", required=True)
    parser.add_argument("--output-prep", required=True)
    parser.add_argument("--output-queue", required=True)
    parser.add_argument("--summary", required=True)
    args = parser.parse_args()
    prep = _load_gzip(Path(args.prep).expanduser())
    queue = json.loads(Path(args.queue).expanduser().read_text(encoding="utf-8"))
    prep, queue = apply_reviews(prep, queue)
    output = Path(args.output_prep).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, "wt", encoding="utf-8", compresslevel=9) as handle:
        json.dump(prep, handle, ensure_ascii=False, separators=(",", ":"))
    Path(args.output_queue).expanduser().write_text(
        json.dumps(queue, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    Path(args.summary).expanduser().write_text(
        json.dumps(prep["summary"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(prep["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
