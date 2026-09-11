#!/usr/bin/env python3
"""Exact-identity canonical-English review overlay for Cook4Me v60 capture.

This module reuses only already-reviewed repository evidence:
- provider food English by exact provider food key;
- entry/title English by exact provider groupingFunctionalId;
- incremental recipe title English by exact (language, provider-native title).

It never creates or changes provider identity and never merges recipe groups from
translated text. Authoritative/native English and explicit operator overrides are
never silently replaced: conflicting reviewed evidence fails closed.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
FOOD_REVIEW = TOOLS / "release_catalog_reviewed_provider_food_english.v2.json"
RECIPE_TITLE_REVIEW = TOOLS / "release_catalog_reviewed_recipe_titles.v1.json"
ENTRY_MEAL_REVIEW = TOOLS / "release_catalog_reviewed_entry_meal_overrides.v1.json"


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", _text(value)).casefold()


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path.name}: expected JSON object")
    return value


@dataclass(frozen=True)
class ReviewBundle:
    provider_foods: dict[str, dict[str, Any]]
    recipe_titles: dict[tuple[str, str], dict[str, Any]]
    entry_titles: dict[str, dict[str, Any]]


def _provider_food_reviews(root: Path) -> dict[str, dict[str, Any]]:
    path = root / FOOD_REVIEW.name
    value = _load_object(path)
    if value.get("kind") != "cook4me-reviewed-provider-food-english":
        raise RuntimeError(f"invalid provider-food English review file: {path.name}")
    out: dict[str, dict[str, Any]] = {}
    for key, raw in (value.get("items") or {}).items():
        if not isinstance(raw, dict):
            continue
        ident = _text(key)
        english = _text(raw.get("english"))
        if not ident or not english:
            continue
        row = dict(raw)
        row["english"] = english
        row["reviewFile"] = path.name
        out[ident] = row
    return out


def _recipe_title_paths(root: Path) -> list[Path]:
    base = root / RECIPE_TITLE_REVIEW.name
    extras = sorted(
        path
        for path in root.glob("release_catalog_reviewed_recipe_titles_*.v1.json")
        if path != base
    )
    return [base, *extras]


def _recipe_title_reviews(root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for path in _recipe_title_paths(root):
        value = _load_object(path)
        if value.get("kind") != "cook4me-reviewed-recipe-title-english":
            raise RuntimeError(f"invalid recipe-title English review file: {path.name}")
        for raw in value.get("items") or []:
            if not isinstance(raw, dict):
                continue
            language = _text(raw.get("language")).lower()
            source = _text(raw.get("source"))
            english = _text(raw.get("english"))
            if not language or not source or not english:
                continue
            key = (language, _norm(source))
            existing = out.get(key)
            if existing and _norm(existing.get("english")) != _norm(english):
                raise RuntimeError(
                    f"conflicting recipe-title review for {language}/{source}: "
                    f"{existing.get('english')!r} vs {english!r}"
                )
            if existing:
                continue
            row = dict(raw)
            row.update(
                {
                    "language": language,
                    "source": source,
                    "english": english,
                    "reviewFile": path.name,
                }
            )
            out[key] = row
    return out


def _entry_title_reviews(root: Path) -> dict[str, dict[str, Any]]:
    path = root / ENTRY_MEAL_REVIEW.name
    value = _load_object(path)
    if value.get("kind") != "cook4me-reviewed-entry-meal-overrides":
        raise RuntimeError(f"invalid entry/meal review file: {path.name}")
    out: dict[str, dict[str, Any]] = {}
    for key, raw in (value.get("items") or {}).items():
        if not isinstance(raw, dict):
            continue
        grouping = _text(key)
        english = _text(raw.get("englishTitle"))
        if not grouping or not english:
            continue
        row = dict(raw)
        row["englishTitle"] = english
        row["reviewFile"] = path.name
        out[grouping] = row
    return out


def load_review_bundle(root: Path = TOOLS) -> ReviewBundle:
    return ReviewBundle(
        provider_foods=_provider_food_reviews(root),
        recipe_titles=_recipe_title_reviews(root),
        entry_titles=_entry_title_reviews(root),
    )


def _set_reviewed_name(
    row: dict[str, Any],
    *,
    reviewed: str,
    source: str,
    confidence: Any,
    review_file: str,
    conflict_label: str,
) -> bool:
    existing = _text(row.get("canonicalName"))
    if existing:
        if _norm(existing) != _norm(reviewed):
            raise RuntimeError(
                f"{conflict_label}: authoritative English {existing!r} conflicts "
                f"with reviewed English {reviewed!r}"
            )
        row.pop("canonicalEnglishNeedsReview", None)
        return False
    row["canonicalName"] = reviewed
    row.setdefault("translations", {}).setdefault("en", reviewed)
    row["canonicalEnglishSource"] = source
    row["canonicalEnglishConfidence"] = _text(confidence) or "reviewed"
    row["canonicalEnglishReviewFile"] = review_file
    row.pop("canonicalEnglishNeedsReview", None)
    return True


def apply_provider_food_reviews(
    ingredients: dict[str, dict[str, Any]],
    reviews: dict[str, dict[str, Any]],
) -> int:
    """Fill missing canonical English only by exact provider ingredient ID."""
    applied = 0
    for ident, row in ingredients.items():
        review = reviews.get(_text(ident))
        if not review:
            continue
        reviewed = _text(review.get("english"))
        if not reviewed:
            continue
        applied += int(
            _set_reviewed_name(
                row,
                reviewed=reviewed,
                source="reviewed:provider-food-english-v2",
                confidence=review.get("confidence"),
                review_file=_text(review.get("reviewFile")),
                conflict_label=f"provider food {_text(ident)}",
            )
        )
    return applied


def _variant_title_key(variant: dict[str, Any]) -> tuple[str, str] | None:
    language = _text(
        variant.get("originalLanguage")
        or variant.get("language")
        or variant.get("sourceCatalogLanguage")
    ).lower()
    title = _text(variant.get("originalTitle") or variant.get("title"))
    if not language or not title:
        return None
    return language, _norm(title)


def apply_recipe_group_reviews(
    groups: dict[str, dict[str, Any]],
    bundle: ReviewBundle,
) -> dict[str, int]:
    """Apply exact grouping/title reviews without changing any group identity."""
    entry_applied = 0
    title_applied = 0

    # Group-ID review is strongest because it is bound directly to provider
    # identity. It may also verify an already-authoritative English title.
    for key, group in groups.items():
        grouping = _text(group.get("groupingFunctionalId")) or _text(key)
        review = bundle.entry_titles.get(grouping)
        if not review:
            continue
        reviewed = _text(review.get("englishTitle"))
        entry_applied += int(
            _set_reviewed_name(
                group,
                reviewed=reviewed,
                source="reviewed:entry-meal-v1",
                confidence=review.get("confidence"),
                review_file=_text(review.get("reviewFile")),
                conflict_label=f"recipe group {grouping}",
            )
        )

    # Exact language/native-title reviews are label evidence only. They can fill
    # an unresolved group but never choose/merge a grouping identity.
    for key, group in groups.items():
        if _text(group.get("canonicalName")):
            continue
        matches: list[dict[str, Any]] = []
        for variant in group.get("variants") or []:
            if not isinstance(variant, dict):
                continue
            title_key = _variant_title_key(variant)
            if title_key and (review := bundle.recipe_titles.get(title_key)):
                matches.append(review)
        if not matches:
            continue
        by_english: dict[str, dict[str, Any]] = {}
        for review in matches:
            by_english.setdefault(_norm(review.get("english")), review)
        if len(by_english) != 1:
            grouping = _text(group.get("groupingFunctionalId")) or _text(key)
            values = sorted({_text(row.get("english")) for row in matches})
            raise RuntimeError(
                f"conflicting exact recipe-title reviews inside provider group "
                f"{grouping}: {values}"
            )
        review = next(iter(by_english.values()))
        reviewed = _text(review.get("english"))
        group["canonicalName"] = reviewed
        group["canonicalEnglishSource"] = "reviewed:recipe-title-v1"
        group["canonicalEnglishConfidence"] = (
            _text(review.get("confidence")) or "reviewed"
        )
        group["canonicalEnglishReviewFile"] = _text(review.get("reviewFile"))
        group.pop("canonicalEnglishNeedsReview", None)
        title_applied += 1

    return {
        "entryMealTitleReviewsApplied": entry_applied,
        "exactRecipeTitleReviewsApplied": title_applied,
    }
