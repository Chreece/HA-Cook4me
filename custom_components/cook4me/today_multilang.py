from __future__ import annotations

from copy import deepcopy
from typing import Any

from .today_logic import ingredient_identities, recipe_identity


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
) -> dict[str, Any] | None:
    best_index: int | None = None
    best_score = float("-inf")
    best_penalty = 0.0
    for index, row in enumerate(bucket):
        ident = recipe_identity(row)
        if ident and ident in seen:
            continue
        penalty = _diversity_penalty(row, chosen) if diversity else 0.0
        selection_score = _score(row) - penalty
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
    match["todayCatalogBalanced"] = True
    return picked


def select_catalog_balanced(
    rows: Any,
    count: int,
    languages: Any,
    *,
    diversity: bool = True,
) -> list[dict[str, Any]]:
    """Select unique recipes while spreading suggestions across chosen catalogs.

    Cross-language variants are intentionally retained until this final stage.
    When enough suggestions are requested and multiple selected catalogs have
    valid candidates, round-robin selection guarantees representation from each
    catalog. Duplicate logical recipes are never emitted merely to satisfy a
    catalog quota.
    """
    candidates = [
        deepcopy(row)
        for row in rows
        if isinstance(row, dict)
    ] if isinstance(rows, list) else []
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
        picked = _pick_best(leftovers, chosen, seen, diversity=diversity)
        if picked is None:
            break
        chosen.append(picked)

    return chosen
