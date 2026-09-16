"""Household/member recipe preferences and explicit ingredient exclusions."""
from copy import deepcopy
import math
import re
from uuid import uuid5, NAMESPACE_URL

DIETS = {"omnivore", "pescatarian", "vegetarian", "vegan"}
TARGETS = {"calorieTarget": 10000, "proteinTarget": 1000, "carbsTarget": 2000,
           "fatTarget": 1000, "saturatedFatTarget": 1000, "sugarsTarget": 1000,
           "fiberTarget": 1000, "saltTarget": 100, "sodiumTarget": 100}
ICONS = {"account", "account-outline", "face-man", "face-woman", "face-man-outline",
         "face-woman-outline", "human-child", "baby-face-outline", "chef-hat", "flower", "star", "heart"}


def text_list(value, limit=250):
    if isinstance(value, str):
        value = value.replace(",", "\n").splitlines()
    return list(dict.fromkeys(x.strip()[:160] for x in value if isinstance(x, str) and x.strip()))[:limit] if isinstance(value, list) else []


def exclusions(value):
    result, seen = [], set()
    for row in value[:500] if isinstance(value, list) else []:
        if not isinstance(row, dict):
            continue
        identity = str(row.get("ingredientId") or row.get("key") or row.get("id") or "")[:160]
        if not identity or identity in seen:
            continue
        seen.add(identity)
        result.append({"ingredientId": identity, "name": str(row.get("name") or identity)[:160],
                       "canonicalName": str(row.get("canonicalName") or row.get("name") or identity)[:160],
                       "sourceIngredientIds": text_list([identity, *(row.get("sourceIngredientIds") if isinstance(row.get("sourceIngredientIds"), list) else [])], 250)})
    return result


def normalize_diet(value, fallback=None):
    data = {**(fallback or {}), **(value if isinstance(value, dict) else {})}
    result = {"diet": data.get("diet") if data.get("diet") in DIETS else "omnivore",
              "nutritionGoal": str(data.get("nutritionGoal") or "balanced")[:40],
              "excludedIngredients": exclusions(data.get("excludedIngredients")),
              "excludedTerms": text_list(data.get("excludedTerms"))}
    for key, maximum in TARGETS.items():
        try:
            number = float(data.get(key))
            result[key] = number if not isinstance(data.get(key), bool) and math.isfinite(number) and 0 <= number <= maximum else None
        except (ValueError, TypeError):
            result[key] = None
    return result


def normalize_profiles(profile):
    data = profile.get("dietProfiles")
    if not isinstance(data, dict):
        household = normalize_diet({"diet": profile.get("diet"),
            "excludedTerms": [*text_list(profile.get("allergies")), *text_list(profile.get("avoid"))]})
        rows = [{"name": name} for name in text_list(profile.get("householdMembers"), 20)]
    else:
        household = normalize_diet(data.get("household"))
        rows = data.get("members") or []
    members, seen = [], set()
    for row in rows[:20] if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not str(row.get("name") or "").strip():
            continue
        name = str(row["name"]).strip()[:80]
        identity = str(row.get("id") or uuid5(NAMESPACE_URL, "cook4me-member:" + name))[:80]
        if not re.fullmatch(r"[\w-]{1,80}", identity) or identity in seen:
            continue
        seen.add(identity)
        members.append({**normalize_diet(row, household), "id": identity, "name": name,
                        "icon": row.get("icon") if row.get("icon") in ICONS else "account"})
    return {"household": household, "members": members}


def resolve_filters(profile, filters):
    """Resolve saved selections server-side; deleted members cannot silently fall back."""
    result = deepcopy(filters)
    source = result.get("dietProfile", "manual")
    if source == "manual":
        return result
    profiles = normalize_profiles(profile)
    selected = profiles["household"] if source == "household" else next(
        (row for row in profiles["members"] if source == "member:" + row["id"]), None)
    if selected is None:
        raise ValueError("This household member no longer exists. Choose a diet profile again.")
    result.update({key: deepcopy(selected[key]) for key in ("diet", "nutritionGoal", "excludedIngredients", "excludedTerms", *TARGETS)})
    return result


def scoring_profile(profile, filters):
    result = deepcopy(profile)
    settings = resolve_filters(profile, filters)
    if settings.get("diet") in DIETS:
        result["diet"] = settings["diet"]
    if "dietProfile" in settings:
        rows = exclusions(settings.get("excludedIngredients"))
        result.update(allergies=[], avoid=text_list([*text_list(settings.get("excludedTerms")),
            *(row["canonicalName"] for row in rows)], 750), excludedIngredients=rows)
    return result
