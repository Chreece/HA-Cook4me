from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from .today_logic import ingredient_identities, recipe_identity
from .recipe_suitability import meal_candidates


def _language(row: dict[str, Any]) -> str:
    return str(row.get("todayCatalogLanguage") or "").strip().lower()


def _score(row: dict[str, Any]) -> float:
    try:
        return float((row.get("match") or {}).get("score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _diversity_penalty(row: dict[str, Any], chosen: list[dict[str, Any]]) -> float:
    ingredients = ingredient_identities(row)
    if not ingredients:
        return 0.0
    max_overlap = 0.0
    for prior in chosen:
        previous = ingredient_identities(prior)
        if not previous:
            continue
        overlap = len(ingredients & previous) / max(1, min(len(ingredients), len(previous)))
        max_overlap = max(max_overlap, overlap)
    return 14.0 * max_overlap


def _pick_best(
    bucket: list[dict[str, Any]],
    chosen: list[dict[str, Any]],
    seen: set[str],
    *,
    diversity: bool,
    daily_targets: Any = None,
    daily_existing: Any = (),
    daily_target_count: int = 1,
) -> dict[str, Any] | None:
    best_index: int | None = None
    best_score = float("-inf")
    best_penalty = 0.0
    for index, row in enumerate(bucket):
        ident = recipe_identity(row)
        if ident and ident in seen:
            continue
        penalty = _diversity_penalty(row, chosen) if diversity else 0.0
        daily_bonus = 0.0
        if isinstance(daily_targets, dict):
            from .nutrient_targets import daily_progress_bonus
            context = [
                item.get("nutrition") or item.get("catalogNutrition") or {}
                for item in [*(daily_existing or ()), *chosen]
                if isinstance(item, dict)
            ]
            hint = daily_progress_bonus(
                context,
                row.get("nutrition") or row.get("catalogNutrition") or {},
                daily_targets,
                fraction=min(1.0, (len(context) + 1) / max(1, int(daily_target_count))),
            )
            daily_bonus = float(hint.get("bonus") or 0.0)
        selection_score = _score(row) - penalty + daily_bonus
        if selection_score > best_score:
            best_index = index
            best_score = selection_score
            best_penalty = penalty
    if best_index is None:
        return None
    picked = bucket.pop(best_index)
    ident = recipe_identity(picked)
    if ident:
        seen.add(ident)
    match = picked.setdefault("match", {})
    match["todayDiversityPenalty"] = round(best_penalty, 1)
    match["todaySelectionScore"] = round(best_score, 1)
    if isinstance(daily_targets, dict):
        from .nutrient_targets import daily_progress_bonus
        context = [
            item.get("nutrition") or item.get("catalogNutrition") or {}
            for item in [*(daily_existing or ()), *chosen]
            if isinstance(item, dict)
        ]
        hint = daily_progress_bonus(
            context,
            picked.get("nutrition") or picked.get("catalogNutrition") or {},
            daily_targets,
            fraction=min(1.0, (len(context) + 1) / max(1, int(daily_target_count))),
        )
        match["dailyNutrientTargetBonus"] = round(float(hint.get("bonus") or 0.0), 2)
    match["todayCatalogBalanced"] = True
    return picked


def select_catalog_balanced(
    rows: Any,
    count: int,
    languages: Any,
    *,
    diversity: bool = True,
    daily_targets: Any = None,
    existing: Any = (),
    overall_count: int | None = None,
) -> list[dict[str, Any]]:
    """Select unique recipes while spreading suggestions across chosen catalogs.

    Cross-language variants are intentionally retained until this final stage.
    When enough suggestions are requested and multiple selected catalogs have
    valid candidates, round-robin selection guarantees representation from each
    catalog. Duplicate logical recipes are never emitted merely to satisfy a
    catalog quota.
    """
    candidates = [deepcopy(row) for row in meal_candidates(rows)]
    target = max(1, min(int(count), 8))

    requested: list[str] = []
    for raw in languages if isinstance(languages, list) else []:
        code = str(raw or "").strip().lower()
        if code and code not in requested:
            requested.append(code)

    buckets: dict[str, list[dict[str, Any]]] = {code: [] for code in requested}
    for row in candidates:
        code = _language(row)
        if not code:
            continue
        buckets.setdefault(code, []).append(row)
    for bucket in buckets.values():
        bucket.sort(key=_score, reverse=True)

    active = [code for code in requested if buckets.get(code)]
    if not active:
        active = [code for code, bucket in buckets.items() if bucket]
    # If fewer suggestions than available catalogs were requested, avoid a fixed
    # "first selected language always wins" bias: start with the strongest
    # available catalog. When target >= catalogs, every catalog still gets a turn.
    if target < len(active):
        active.sort(key=lambda code: _score(buckets[code][0]), reverse=True)

    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    while active and len(chosen) < target:
        progressed = False
        for code in active:
            if len(chosen) >= target:
                break
            picked = _pick_best(
                buckets.get(code, []),
                chosen,
                seen,
                diversity=diversity,
                daily_targets=daily_targets,
                daily_existing=existing,
                daily_target_count=overall_count or target,
            )
            if picked is None:
                continue
            chosen.append(picked)
            progressed = True
        if not progressed:
            break

    # There can be leftovers from a catalog after another catalog ran out of
    # unique recipes. Fill the requested count by score without reintroducing a
    # duplicate logical recipe.
    leftovers: list[dict[str, Any]] = []
    for bucket in buckets.values():
        leftovers.extend(bucket)
    while leftovers and len(chosen) < target:
        picked = _pick_best(
            leftovers, chosen, seen, diversity=diversity,
            daily_targets=daily_targets, daily_existing=existing,
            daily_target_count=overall_count or target,
        )
        if picked is None:
            break
        chosen.append(picked)

    return chosen


def select_today_categories(rows, categories, languages, previous=(), history=(), daily_targets=None):
    """Rotate eligible families across requests, then balance their catalogs.

    History affects selection only after diet, pantry and other filters have
    run. Exhausted categories reuse the least recently suggested family; a
    translation or serving edition never counts as a new recipe.
    """
    from .today_logic import normalize_meal_types, recipe_matches_meal_types
    rows = meal_candidates(rows)
    identity = lambda row: row.get("displayFamilyId") or recipe_identity(row)
    recent = compact_suggestion_history(history)
    if not recent:
        recent = [{"familyId": str(identity(row)), "language": _language(row)}
                  for row in previous if isinstance(row, dict) and identity(row)]
    last_seen = {row["familyId"]: index for index, row in enumerate(recent)}
    language_counts = Counter(row["language"] for row in recent)
    chosen, seen, counts = [], set(), {}
    normalized_categories = normalize_meal_types(categories)
    for category in normalized_categories:
        matching = [row for row in rows if recipe_matches_meal_types(row, [category])]
        counts[category] = len({identity(row) for row in matching})
        pool = [row for row in matching if identity(row) not in seen]
        if not pool:
            continue
        oldest = min(last_seen.get(str(identity(row)), -1) for row in pool)
        pool = [row for row in pool if last_seen.get(str(identity(row)), -1) == oldest]
        least_used = min(language_counts[_language(row)] for row in pool)
        pool = [row for row in pool if language_counts[_language(row)] == least_used]
        selected = select_catalog_balanced(
            pool, 1, languages,
            daily_targets=daily_targets,
            existing=chosen,
            overall_count=max(1, len(normalized_categories)),
        )
        if selected:
            row = selected[0]
            row["todayMealType"] = category
            seen.add(identity(row))
            chosen.append(row)
            language_counts[_language(row)] += 1
    recent.extend({"familyId": str(identity(row)), "language": _language(row)} for row in chosen)
    return {"items": chosen, "categoryCounts": counts,
        "suggestionHistory": compact_suggestion_history(recent),
        "emptyMealTypes": [category for category in counts if not any(row["todayMealType"] == category for row in chosen)]}


def compact_suggestion_history(value):
    """A bounded record of suggested families, separate from meals cooked."""
    if not isinstance(value, (list, tuple)):
        return []
    return [{"familyId": str(row["familyId"])[:200], "language": str(row.get("language") or "")[:16]}
            for row in value[-256:] if isinstance(row, dict) and row.get("familyId")]
