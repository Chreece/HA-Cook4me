from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .nutrition import (
    DEMO_KEY,
    _fdc_candidate_score,
    _norm,
    _text,
    nutrition_from_fdc_food,
)

_FDC_BASE = "https://api.nal.usda.gov/fdc/v1/foods/search"
_MIN_SCORE = 0.86
_MIN_MARGIN = 0.05


def ranked_fdc_candidates(query: str, foods: Any) -> list[tuple[float, dict[str, Any]]]:
    """Rank distinct FDC descriptions so duplicate rows do not fake ambiguity."""
    if not isinstance(foods, list):
        return []
    best_by_description: dict[str, tuple[float, dict[str, Any]]] = {}
    for food in foods:
        if not isinstance(food, dict):
            continue
        description = _norm(food.get("description"))
        if not description:
            continue
        score = _fdc_candidate_score(query, food)
        if score <= 0:
            continue
        previous = best_by_description.get(description)
        if previous is None or score > previous[0]:
            best_by_description[description] = (score, food)
    return sorted(best_by_description.values(), key=lambda item: item[0], reverse=True)


def select_fdc_candidate_strict(
    query: str,
    foods: Any,
    *,
    min_score: float = _MIN_SCORE,
    min_margin: float = _MIN_MARGIN,
) -> tuple[dict[str, Any] | None, float, float | None]:
    """Select only an FDC candidate that is both strong and unambiguous.

    The old matcher accepted the highest result above a score threshold even if
    a second, semantically different preparation had the same score.  Generic
    nutrition is allowed to remain unknown instead of choosing arbitrarily.
    An exact normalized description match is authoritative enough to skip the
    runner-up margin requirement.
    """
    ranked = ranked_fdc_candidates(query, foods)
    if not ranked:
        return None, 0.0, None
    top_score, top = ranked[0]
    runner_score = ranked[1][0] if len(ranked) > 1 else None
    if top_score < min_score:
        return None, top_score, runner_score

    query_norm = _norm(query)
    top_norm = _norm(top.get("description"))
    if top_norm == query_norm:
        return top, top_score, runner_score

    if runner_score is not None and top_score - runner_score < min_margin:
        return None, top_score, runner_score
    return top, top_score, runner_score


def lookup_food_data_central_strict(
    query: str,
    api_key: str = DEMO_KEY,
    timeout: int = 20,
) -> dict[str, Any]:
    query = _text(query)
    if not query:
        return {"ok": False, "reason": "empty_query"}
    body = json.dumps(
        {
            "query": query,
            "pageSize": 12,
            "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
        }
    ).encode("utf-8")
    url = f"{_FDC_BASE}?{urllib.parse.urlencode({'api_key': api_key or DEMO_KEY})}"
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "reason": f"http_{exc.code}"}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "reason": type(exc).__name__}

    food, score, runner_score = select_fdc_candidate_strict(query, payload.get("foods"))
    margin = None if runner_score is None else score - runner_score
    if food is None:
        return {
            "ok": False,
            "reason": "ambiguous",
            "confidence": round(score, 3),
            "runnerUpConfidence": round(runner_score, 3) if runner_score is not None else None,
            "confidenceMargin": round(margin, 3) if margin is not None else None,
        }

    nutrition = nutrition_from_fdc_food(food, query=query)
    if nutrition is None:
        return {
            "ok": False,
            "reason": "no_nutrition",
            "confidence": round(score, 3),
            "runnerUpConfidence": round(runner_score, 3) if runner_score is not None else None,
            "confidenceMargin": round(margin, 3) if margin is not None else None,
        }
    return {
        "ok": True,
        "query": query,
        "confidence": round(score, 3),
        "runnerUpConfidence": round(runner_score, 3) if runner_score is not None else None,
        "confidenceMargin": round(margin, 3) if margin is not None else None,
        "fdcId": food.get("fdcId"),
        "description": food.get("description"),
        "dataType": food.get("dataType"),
        "nutrition": nutrition,
    }
