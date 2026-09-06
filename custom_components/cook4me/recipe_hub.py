from __future__ import annotations

import asyncio
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .recipe_logic import normalize_manual_recipe, normalize_text, recipe_ingredient_names, score_recipe

_STORAGE_VERSION = 1

_DEFAULT_PROFILE: dict[str, Any] = {
    "diet": "omnivore",
    "allergies": [],
    "avoid": [],
    "preferences": [],
    # ``pantry`` is retained for storage/API compatibility with older releases.
    # v13 presents this as "what I have in my house" and additionally stores
    # exact SEB MarketingFood selections in pantryItems.
    "pantry": [],
    "pantryItems": [],
}

_DEFAULT_UI_PREFERENCES: dict[str, Any] = {
    "catalogLanguage": "auto",
    "ingredientCatalogLanguage": "auto",
    "translateResults": True,
    "lastTab": "official",
    # Per logical recipe selections are bounded below. They let the same card
    # remember its preferred source language and serving across panel reloads.
    "recipeLanguageSelections": {},
    "recipeServingSelections": {},
}

_ALLOWED_TABS = {"official", "recommend", "mine", "profile", "ai"}


class Cook4MeRecipeHub:
    """Persist Cook4Me house ingredients/preferences, recipes, and UI state."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store[dict[str, Any]] = Store(
            hass, _STORAGE_VERSION, f"{DOMAIN}.{entry_id}.recipe_hub"
        )
        self._lock = asyncio.Lock()
        self._data: dict[str, Any] = {
            "profile": deepcopy(_DEFAULT_PROFILE),
            "recipes": [],
            "history": [],
            "uiPreferences": deepcopy(_DEFAULT_UI_PREFERENCES),
        }

    async def async_load(self) -> None:
        saved = await self._store.async_load()
        if not isinstance(saved, dict):
            return
        profile = saved.get("profile")
        if isinstance(profile, dict):
            merged = deepcopy(_DEFAULT_PROFILE)
            merged.update(profile)
            self._data["profile"] = self._normalize_profile(merged)
        recipes = saved.get("recipes")
        if isinstance(recipes, list):
            self._data["recipes"] = [x for x in recipes if isinstance(x, dict)]
        history = saved.get("history")
        if isinstance(history, list):
            self._data["history"] = [x for x in history[-100:] if isinstance(x, dict)]
        ui_preferences = saved.get("uiPreferences")
        if isinstance(ui_preferences, dict):
            merged_ui = deepcopy(_DEFAULT_UI_PREFERENCES)
            merged_ui.update(ui_preferences)
            self._data["uiPreferences"] = self._normalize_ui_preferences(merged_ui)

    @staticmethod
    def _normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
        diet = str(profile.get("diet") or "omnivore").lower()
        if diet not in {"omnivore", "pescatarian", "vegetarian", "vegan"}:
            diet = "omnivore"
        out: dict[str, Any] = {"diet": diet}
        for key in ("allergies", "avoid", "preferences", "pantry"):
            values = profile.get(key) or []
            if isinstance(values, str):
                values = [x.strip() for x in values.replace(",", "\n").splitlines()]
            out[key] = list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))[:250]

        pantry_items: list[dict[str, str]] = []
        seen_items: set[tuple[str, str]] = set()
        raw_items = profile.get("pantryItems") or []
        if isinstance(raw_items, list):
            for raw in raw_items[-500:]:
                if not isinstance(raw, dict):
                    continue
                item_id = str(raw.get("id") or raw.get("key") or "").strip()[:160]
                name = str(raw.get("name") or "").strip()[:240]
                language = str(raw.get("language") or "").strip().lower().replace("_", "-").split("-", 1)[0][:12]
                if not name:
                    continue
                identity = (item_id, normalize_text(name))
                if identity in seen_items:
                    continue
                seen_items.add(identity)
                item = {"name": name}
                if item_id:
                    item["id"] = item_id
                if language:
                    item["language"] = language
                pantry_items.append(item)
        out["pantryItems"] = pantry_items[:500]
        return out

    @staticmethod
    def _normalize_ui_preferences(preferences: dict[str, Any]) -> dict[str, Any]:
        def source_language(key: str) -> str:
            language = str(preferences.get(key) or "auto").strip().lower().replace("_", "-")
            if language != "auto":
                language = language.split("-", 1)[0][:12]
                if not language.isalpha():
                    language = "auto"
            return language

        tab = str(preferences.get("lastTab") or "official").strip().lower()
        if tab not in _ALLOWED_TABS:
            tab = "official"

        def selection_map(value: Any, *, max_value_length: int) -> dict[str, str]:
            if not isinstance(value, dict):
                return {}
            out: dict[str, str] = {}
            for raw_key, raw_value in list(value.items())[-250:]:
                key = str(raw_key or "").strip()[:160]
                selected = str(raw_value or "").strip()[:max_value_length]
                if key and selected:
                    out[key] = selected
            return out

        return {
            "catalogLanguage": source_language("catalogLanguage"),
            "ingredientCatalogLanguage": source_language("ingredientCatalogLanguage"),
            "translateResults": bool(preferences.get("translateResults", True)),
            "lastTab": tab,
            "recipeLanguageSelections": selection_map(
                preferences.get("recipeLanguageSelections"), max_value_length=12
            ),
            "recipeServingSelections": selection_map(
                preferences.get("recipeServingSelections"), max_value_length=32
            ),
        }

    async def _save(self) -> None:
        await self._store.async_save(self._data)

    def snapshot(self) -> dict[str, Any]:
        return deepcopy(self._data)

    @property
    def profile(self) -> dict[str, Any]:
        return deepcopy(self._data["profile"])

    @property
    def recipes(self) -> list[dict[str, Any]]:
        return deepcopy(self._data["recipes"])

    @property
    def ui_preferences(self) -> dict[str, Any]:
        return deepcopy(self._data["uiPreferences"])

    @property
    def habit_terms(self) -> list[str]:
        return self._habit_terms()

    async def async_set_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            merged = deepcopy(self._data["profile"])
            merged.update(profile)
            self._data["profile"] = self._normalize_profile(merged)
            await self._save()
            return self.profile

    async def async_set_ui_preferences(self, preferences: dict[str, Any]) -> dict[str, Any]:
        """Persist Recipe Hub display controls without touching dietary profile data."""
        async with self._lock:
            merged = deepcopy(self._data["uiPreferences"])
            merged.update(preferences)
            self._data["uiPreferences"] = self._normalize_ui_preferences(merged)
            await self._save()
            return self.ui_preferences

    async def async_save_recipe(self, recipe: dict[str, Any], *, source: str = "manual") -> dict[str, Any]:
        normalized = normalize_manual_recipe(recipe, source=source)
        if source == "ai":
            match = score_recipe(normalized, self._scoring_profile())
            if not match.get("safe"):
                conflicts = ", ".join(match.get("violations") or []) or "saved dietary profile"
                raise ValueError(f"AI recipe conflicts with Cook4Me dietary profile: {conflicts}")
        now = datetime.now(timezone.utc).isoformat()
        recipe_id = str(recipe.get("id") or uuid4())
        normalized.update(
            {
                "id": recipe_id,
                "createdAt": str(recipe.get("createdAt") or now),
                "updatedAt": now,
            }
        )
        async with self._lock:
            items = self._data["recipes"]
            for index, current in enumerate(items):
                if current.get("id") == recipe_id:
                    normalized["createdAt"] = current.get("createdAt") or normalized["createdAt"]
                    items[index] = normalized
                    break
            else:
                items.append(normalized)
            self._data["recipes"] = items[-250:]
            await self._save()
        return deepcopy(normalized)

    async def async_delete_recipe(self, recipe_id: str) -> bool:
        async with self._lock:
            before = len(self._data["recipes"])
            self._data["recipes"] = [x for x in self._data["recipes"] if x.get("id") != recipe_id]
            changed = len(self._data["recipes"]) != before
            if changed:
                await self._save()
            return changed

    async def async_record_send(self, recipe: dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "title": recipe.get("title"),
            "groupingFunctionalId": recipe.get("groupingFunctionalId"),
            "recipeFunctionalId": recipe.get("recipeFunctionalId"),
            "variantFunctionalId": recipe.get("variantFunctionalId") or recipe.get("recipeFunctionalId"),
            "ingredientNames": recipe_ingredient_names(recipe)[:80],
            "courses": deepcopy(recipe.get("courses") or [])[:20],
        }
        async with self._lock:
            self._data["history"] = (self._data["history"] + [entry])[-100:]
            await self._save()

    def _habit_terms(self) -> list[str]:
        """Return frequent past-send terms as ranking-only hints, never safety rules."""
        counts: Counter[str] = Counter()
        original: dict[str, str] = {}
        for entry in self._data.get("history", [])[-30:]:
            if not isinstance(entry, dict):
                continue
            for value in entry.get("ingredientNames") or []:
                term = normalize_text(value)
                if term:
                    counts[term] += 1
                    original.setdefault(term, str(value))
            for value in entry.get("courses") or []:
                if isinstance(value, dict):
                    value = value.get("name") or value.get("key")
                term = normalize_text(value)
                if term:
                    counts[term] += 1
                    original.setdefault(term, str(value))
        return [original[t] for t, count in counts.most_common(12) if count >= 2]

    def _scoring_profile(self) -> dict[str, Any]:
        profile = deepcopy(self._data["profile"])
        # Exact MarketingFood selections participate in the existing localized
        # name matcher while their stable SEB ids remain persisted separately.
        house_names = [
            str(item.get("name") or "").strip()
            for item in profile.get("pantryItems") or []
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        ]
        profile["pantry"] = list(dict.fromkeys([*profile.get("pantry", []), *house_names]))
        profile["habitTerms"] = self._habit_terms()
        return profile

    def annotate(self, recipe: dict[str, Any]) -> dict[str, Any]:
        result = deepcopy(recipe)
        result["match"] = score_recipe(result, self._scoring_profile())
        return result

    def rank(self, recipes: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
        scored = [self.annotate(x) for x in recipes if isinstance(x, dict)]
        safe = [x for x in scored if x.get("match", {}).get("safe")]
        safe.sort(key=lambda x: x.get("match", {}).get("score", -1000), reverse=True)
        return safe[: max(1, min(int(limit), 50))]
