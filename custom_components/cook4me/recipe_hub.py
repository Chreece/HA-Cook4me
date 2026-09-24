from __future__ import annotations

import asyncio
from collections import Counter
from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .food_intelligence import recipe_quantity_feasibility
from .ingredient_catalog import enrich_match_with_house_keys
from .inventory import (
    DEFAULT_EXPIRY_WARNING_DAYS,
    add_inventory_item,
    inventory_identity,
    apply_consumption,
    consumption_shortfalls,
    restore_consumption,
    normalize_inventory,
    recipe_consumption_items,
    recipe_expiry_priority,
    remove_inventory_item,
    update_inventory_item,
)
from .recipe_logic import normalize_manual_recipe, normalize_text, recipe_ingredient_names, score_recipe
from .storage_locations import normalize_locations, edit_location, validate_location

_STORAGE_VERSION = 1

_DEFAULT_PROFILE: dict[str, Any] = {
    "diet": "omnivore",
    "allergies": [],
    "avoid": [],
    "preferences": [],
    "householdMembers": [],
    # pantry is retained for storage/backwards compatibility. New UI writes the
    # structured houseIngredients stock list; pantry mirrors display names for
    # older ranking/AI code.
    "pantry": [],
    "houseIngredients": [],
}

_DEFAULT_UI_PREFERENCES: dict[str, Any] = {
    "catalogLanguage": "auto",
    "translateResults": True,
    "lastTab": "official",
    "nutritionGoal": "balanced",
    "recipeLanguageSelections": {},
    "recipeServingSelections": {},
}

_ALLOWED_TABS = {"official", "recommend", "mine", "profile", "shopping", "ai"}
_ALLOWED_NUTRITION_GOALS = {
    "balanced",
    "high_protein",
    "lower_calorie",
    "high_fiber",
    "lower_saturated_fat",
}


class Cook4MeRecipeHub:
    """Persist Cook4Me house inventory/preferences, recipes, and Recipe Hub UI state."""

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
            "userUiPreferences": {},
            "pendingConsumption": None,
        }

    async def async_load(self) -> None:
        saved = await self._store.async_load()
        if not isinstance(saved, dict):
            return
        # Receipt drafts can be resumed long after the 200 ordinary scan retries.
        pinned = saved.get("receiptScannerReceipts")
        if isinstance(pinned, dict):
            self._data["receiptScannerReceipts"] = deepcopy(pinned)
        receipts = saved.get("scannerReceipts")
        if isinstance(receipts, dict):
            self._data["scannerReceipts"] = dict(list(receipts.items())[-200:])
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
        pending = saved.get("pendingConsumption")
        from .shared_recipe_filters import normalize_preferences
        users = saved.get("userUiPreferences")
        if isinstance(users, dict):
            self._data["userUiPreferences"] = {str(key): normalize_preferences(value) for key, value in users.items()}
        if isinstance(pending, dict) and isinstance(pending.get("ingredients"), list):
            self._data["pendingConsumption"] = deepcopy(pending)

    @staticmethod
    def _normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
        diet = str(profile.get("diet") or "omnivore").lower()
        if diet not in {"omnivore", "pescatarian", "vegetarian", "vegan"}:
            diet = "omnivore"
        out: dict[str, Any] = {"diet": diet}
        for key in ("allergies", "avoid", "preferences"):
            values = profile.get(key) or []
            if isinstance(values, str):
                values = [x.strip() for x in values.replace(",", "\n").splitlines()]
            out[key] = list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))[:250]

        members = profile.get("householdMembers") or []
        if isinstance(members, str):
            members = [x.strip() for x in members.replace(",", "\n").splitlines()]
        out["householdMembers"] = list(
            dict.fromkeys(str(x).strip() for x in members if str(x).strip())
        )[:20]

        from .diet_profiles import normalize_profiles
        out["dietProfiles"] = normalize_profiles(profile)
        if isinstance(profile.get("dietProfiles"), dict):
            household = out["dietProfiles"]["household"]
            out["diet"] = household["diet"]
            out["allergies"] = []
            out["avoid"] = list(dict.fromkeys([*household["excludedTerms"],
                *(row["canonicalName"] for row in household["excludedIngredients"])]))
            out["householdMembers"] = [row["name"] for row in out["dietProfiles"]["members"]]
        out["excludedIngredients"] = out["dietProfiles"]["household"]["excludedIngredients"]
        house = normalize_inventory(profile.get("houseIngredients"))
        if not house:
            # Seamless migration from the old free-text pantry list.
            house = normalize_inventory(profile.get("pantry"))
        out["houseIngredients"] = house
        out["pantry"] = [row["name"] for row in house]
        out["storageLocations"] = normalize_locations(profile.get("storageLocations"))
        out["scannerAiTaskEntityId"] = str(profile.get("scannerAiTaskEntityId") or "")[:160]
        return out

    @staticmethod
    def _normalize_ui_preferences(preferences: dict[str, Any]) -> dict[str, Any]:
        language = str(preferences.get("catalogLanguage") or "auto").strip().lower().replace("_", "-")
        if language != "auto":
            language = language.split("-", 1)[0][:12]
            if not language.isalpha():
                language = "auto"

        tab = str(preferences.get("lastTab") or "official").strip().lower()
        if tab not in _ALLOWED_TABS:
            tab = "official"
        nutrition_goal = str(preferences.get("nutritionGoal") or "balanced").strip().lower()
        if nutrition_goal not in _ALLOWED_NUTRITION_GOALS:
            nutrition_goal = "balanced"

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
            "catalogLanguage": language,
            "translateResults": bool(preferences.get("translateResults", True)),
            "lastTab": tab,
            "nutritionGoal": nutrition_goal,
            "recipeLanguageSelections": selection_map(
                preferences.get("recipeLanguageSelections"), max_value_length=12
            ),
            "recipeServingSelections": selection_map(
                preferences.get("recipeServingSelections"), max_value_length=32
            ),
        }

    async def _save(self) -> None:
        await self._store.async_save(deepcopy(self._data))

    @asynccontextmanager
    async def _durable_mutation(self):
        """Serialize one in-place mutation and roll memory back on failed storage."""
        async with self._lock:
            before = deepcopy(self._data)
            try:
                yield
            except BaseException:
                self._data = before
                raise

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
    def pending_consumption(self) -> dict[str, Any] | None:
        pending = self._data.get("pendingConsumption")
        return deepcopy(pending) if isinstance(pending, dict) else None

    @property
    def habit_terms(self) -> list[str]:
        return self._habit_terms()

    async def async_set_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        async with self._durable_mutation():
            merged = deepcopy(self._data["profile"])
            # Storage mutations need their own locked referential checks.
            merged.update({key: value for key, value in profile.items() if key != "storageLocations"})
            if "dietProfiles" not in profile and any(key in profile for key in ("diet", "allergies", "avoid", "householdMembers")):
                from .diet_profiles import normalize_profiles, normalize_diet, text_list
                diets = normalize_profiles(merged)
                if "diet" in profile:
                    diets["household"]["diet"] = merged["diet"]
                if "allergies" in profile or "avoid" in profile:
                    diets["household"]["excludedTerms"] = list(dict.fromkeys([*text_list(merged.get("allergies")), *text_list(merged.get("avoid"))]))
                if "householdMembers" in profile:
                    old = {row["name"]: row for row in diets["members"]}
                    migration = normalize_profiles({"diet": merged.get("diet"), "householdMembers": profile["householdMembers"]})
                    diets["members"] = [old.get(row["name"], {**row, **normalize_diet(diets["household"])}) for row in migration["members"]]
                merged["dietProfiles"] = diets
            self._data["profile"] = self._normalize_profile(merged)
            await self._save()
            return self.profile

    async def async_storage_location(self, **change) -> dict[str, Any]:
        async with self._lock:
            data = deepcopy(self._data)
            data["profile"] = self._normalize_profile(edit_location(data["profile"], **change))
            await self._store.async_save(data)
            self._data = data
            return self.profile

    async def async_scanner_add(self, request_id, ingredient, *, quantity, unit,
                                best_before="", lot_metadata=None, fingerprint="", package_count=1,
                                unlimited=False):
        """Commit reviewed stock once, including across reconnect/restart retries."""
        async with self._lock:
            receipts = self._data.get("scannerReceipts") or {}
            pinned = self._data.get("receiptScannerReceipts") or {}
            if request_id in receipts or request_id in pinned:
                receipt = pinned.get(request_id) or receipts[request_id]
                if receipt.get("fingerprint") != fingerprint:
                    raise ValueError("This product was already saved; start a new product")
                return deepcopy(receipt)
            receipt_request = str(request_id).startswith("receipt-")
            if receipt_request and len(pinned) >= 8192:
                raise ValueError("Finish and discard old receipt drafts before adding another receipt item")
            data = deepcopy(self._data)
            profile = data["profile"]
            metadata = validate_location(profile, lot_metadata)
            if isinstance(package_count, bool) or not isinstance(package_count, int) or not 1 <= package_count <= 100:
                raise ValueError("Choose between 1 and 100 packages")
            if unlimited and package_count != 1:
                raise ValueError("Unlimited stock is one logical stock item, not multiple packages")
            if unlimited:
                profile["houseIngredients"] = add_inventory_item(
                    profile.get("houseIngredients"), ingredient, quantity=None, unit=unit,
                    unlimited=True, best_before=best_before, lot_metadata=None)
                lot_ids = []
            else:
                if any(row.get("unlimited") and inventory_identity(row) == inventory_identity(ingredient)
                       for row in profile.get("houseIngredients") or []):
                    raise ValueError("This ingredient has unlimited stock. Switch it to a measured amount before adding packages")
                lot_ids = []
                for _ in range(package_count):
                    metadata["id"] = str(uuid4())
                    lot_ids.append(metadata["id"])
                    profile["houseIngredients"] = add_inventory_item(
                        profile.get("houseIngredients"), ingredient, quantity=quantity, unit=unit,
                        unlimited=False, best_before=best_before, lot_metadata=metadata)
            profile["pantry"] = [row["name"] for row in profile["houseIngredients"]]
            data["profile"] = self._normalize_profile(profile)
            if unlimited:
                saved = next((row for row in data["profile"]["houseIngredients"]
                              if inventory_identity(row) == inventory_identity(ingredient)), None)
                if not saved or not saved.get("unlimited"):
                    raise ValueError("The unlimited stock item could not be saved")
            else:
                saved_ids = {lot.get("id") for row in data["profile"]["houseIngredients"] for lot in row.get("lots") or []}
                if not all(lot_id in saved_ids for lot_id in lot_ids):
                    raise ValueError("The stock list is full or the amount is invalid; the product was not added")
            receipt = {"lotId": lot_ids[0] if lot_ids else "", "lotIds": lot_ids,
                       "unlimited": bool(unlimited), "fingerprint": fingerprint}
            if receipt_request:
                data["receiptScannerReceipts"] = {**pinned, request_id: receipt}
            else:
                data["scannerReceipts"] = dict(list({**receipts, request_id: receipt}.items())[-200:])
            await self._store.async_save(data)
            self._data = data
            return deepcopy(receipt)

    async def async_release_receipt_requests(self, receipt_id):
        """Release retry records only after the owning draft has been deleted."""
        prefix = f"receipt-{receipt_id}-"
        async with self._lock:
            data = deepcopy(self._data)
            data["receiptScannerReceipts"] = {
                key: row for key, row in data.get("receiptScannerReceipts", {}).items()
                if not key.startswith(prefix)
            }
            await self._store.async_save(data)
            self._data = data

    async def async_scanner_update(self, request_id, ingredient, *, lot_id, expected_version,
                                   quantity, unit, best_before="", lot_metadata=None, fingerprint=""):
        """Edit one stable package without overwriting its siblings or newer edits."""
        from .product_packages import find_package, package_version
        async with self._lock:
            data = deepcopy(self._data)
            profile = data["profile"]
            house = profile.get("houseIngredients") or []
            row, lot = find_package(house, lot_id)
            receipts = data.get("scannerReceipts") or {}
            previous = receipts.get(request_id)
            if previous:
                if previous.get("fingerprint") != fingerprint or previous.get("version") != package_version(row, lot):
                    raise ValueError("This package changed after saving; reload it before editing again")
                return deepcopy(previous)
            if expected_version != package_version(row, lot):
                raise ValueError("This package changed while you were editing it; reload it before saving")
            if any(item.get("unlimited") and inventory_identity(item) == inventory_identity(ingredient) for item in house):
                raise ValueError("Switch unlimited stock to a measured amount before moving packages here")
            metadata = validate_location(profile, lot_metadata)
            metadata.update(id=lot_id, addedAt=lot.get("addedAt"), revision=str(uuid4()))
            remaining = [item for item in row.get("lots") or [] if item.get("id") != lot_id]
            if remaining:
                house = update_inventory_item(house, inventory_identity(row), unit=row.get("unit", ""), lots=remaining)
            else:
                house = remove_inventory_item(house, inventory_identity(row))
            house = add_inventory_item(house, ingredient, quantity=quantity, unit=unit,
                                       best_before=best_before, lot_metadata=metadata)
            profile["houseIngredients"] = house
            profile["pantry"] = [item["name"] for item in house]
            data["profile"] = self._normalize_profile(profile)
            current, saved = find_package(data["profile"]["houseIngredients"], lot_id)
            receipt = {"lotId": lot_id, "fingerprint": fingerprint, "version": package_version(current, saved)}
            data["scannerReceipts"] = dict(list({**receipts, request_id: receipt}.items())[-200:])
            await self._store.async_save(data)
            self._data = data
            return deepcopy(receipt)

    async def async_package_remove(self, lot_id, expected_version):
        from .product_packages import find_package, package_version
        async with self._lock:
            data = deepcopy(self._data)
            profile = data["profile"]
            house = profile.get("houseIngredients") or []
            try:
                row, lot = find_package(house, lot_id)
            except ValueError:
                return self.profile  # The same removal can be retried safely.
            if expected_version != package_version(row, lot):
                raise ValueError("This package changed; reload it before removing it")
            remaining = [item for item in row.get("lots") or [] if item.get("id") != lot_id]
            profile["houseIngredients"] = (update_inventory_item(house, inventory_identity(row), unit=row.get("unit", ""), lots=remaining)
                                            if remaining else remove_inventory_item(house, inventory_identity(row)))
            profile["pantry"] = [item["name"] for item in profile["houseIngredients"]]
            data["profile"] = self._normalize_profile(profile)
            await self._store.async_save(data)
            self._data = data
            return self.profile

    async def async_inventory_add(
        self,
        ingredient: dict[str, Any],
        *,
        quantity: Any = None,
        unit: str = "",
        unlimited: bool = False,
        best_before: str = "",
        lot_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with self._durable_mutation():
            profile = deepcopy(self._data["profile"])
            lot_metadata = validate_location(profile, lot_metadata)
            house = add_inventory_item(
                profile.get("houseIngredients"),
                ingredient,
                quantity=quantity,
                unit=unit,
                unlimited=unlimited,
                best_before=best_before,
                lot_metadata=lot_metadata,
            )
            profile["houseIngredients"] = house
            profile["pantry"] = [row["name"] for row in house]
            self._data["profile"] = self._normalize_profile(profile)
            await self._save()
            return self.profile

    async def async_inventory_update(
        self,
        identity: str,
        *,
        quantity: Any = None,
        unit: str = "",
        unlimited: bool = False,
        best_before: Any = None,
        lots: Any = None,
    ) -> dict[str, Any]:
        async with self._durable_mutation():
            profile = deepcopy(self._data["profile"])
            kwargs: dict[str, Any] = {}
            if best_before is not None:
                kwargs["best_before"] = best_before
            if lots is not None:
                kwargs["lots"] = [validate_location(profile, lot) for lot in lots]
            house = update_inventory_item(
                profile.get("houseIngredients"),
                identity,
                quantity=quantity,
                unit=unit,
                unlimited=unlimited,
                **kwargs,
            )
            profile["houseIngredients"] = house
            profile["pantry"] = [row["name"] for row in house]
            self._data["profile"] = self._normalize_profile(profile)
            await self._save()
            return self.profile

    async def async_inventory_remove(self, identity: str) -> dict[str, Any]:
        async with self._durable_mutation():
            profile = deepcopy(self._data["profile"])
            house = remove_inventory_item(profile.get("houseIngredients"), identity)
            profile["houseIngredients"] = house
            profile["pantry"] = [row["name"] for row in house]
            self._data["profile"] = self._normalize_profile(profile)
            await self._save()
            return self.profile

    async def async_prepare_consumption(self, recipe: dict[str, Any]) -> dict[str, Any] | None:
        ingredients = recipe_consumption_items(
            recipe, self._data["profile"].get("houseIngredients")
        )
        if not ingredients:
            return None
        servings = recipe.get("servings") or recipe.get("groupSize")
        yield_data = recipe.get("yield") if isinstance(recipe.get("yield"), dict) else {}
        servings = servings or yield_data.get("quantity") or yield_data.get("quantityDisplay")
        pending = {
            "id": str(uuid4()),
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "recipeTitle": str(recipe.get("title") or "Cook4Me recipe"),
            "groupingFunctionalId": recipe.get("groupingFunctionalId"),
            "variantFunctionalId": recipe.get("variantFunctionalId") or recipe.get("recipeFunctionalId"),
            "servings": servings,
            "recipeIngredients": deepcopy(recipe.get("ingredients") or []),
            "ingredients": ingredients,
        }
        async with self._durable_mutation():
            self._data["pendingConsumption"] = pending
            await self._save()
        return deepcopy(pending)

    async def async_confirm_consumption(
        self,
        pending_id: str,
        consumptions: list[dict[str, Any]],
        *,
        strict: bool = False,
    ) -> dict[str, Any]:
        async with self._durable_mutation():
            pending = self._data.get("pendingConsumption")
            if not isinstance(pending, dict) or str(pending.get("id")) != str(pending_id):
                raise ValueError("Consumption confirmation is no longer pending")
            completed = deepcopy(pending)
            profile = deepcopy(self._data["profile"])
            house, report = apply_consumption(
                profile.get("houseIngredients"), consumptions
            )
            if strict:
                shortfalls = consumption_shortfalls(consumptions, report)
                if shortfalls:
                    raise ValueError(
                        "The selected storage amount is no longer available; reload stock and review the deduction"
                    )
            profile["houseIngredients"] = house
            profile["pantry"] = [row["name"] for row in house]
            self._data["profile"] = self._normalize_profile(profile)
            self._data["pendingConsumption"] = None
            await self._save()
            return {"profile": self.profile, "report": report, "completedRecipe": completed}

    async def async_revise_consumption(
        self,
        previous_report: dict[str, Any],
        consumptions: list[dict[str, Any]],
        *,
        strict: bool = False,
    ) -> dict[str, Any]:
        """Atomically restore an old meal deduction and apply the edited mapping."""
        async with self._durable_mutation():
            profile = deepcopy(self._data["profile"])
            restored_house, restored = restore_consumption(
                profile.get("houseIngredients"), previous_report
            )
            house, report = apply_consumption(restored_house, consumptions)
            if strict:
                shortfalls = consumption_shortfalls(consumptions, report)
                if shortfalls:
                    raise ValueError(
                        "The edited storage amount cannot be fully deducted; review the selected ingredient or lot"
                    )
            profile["houseIngredients"] = house
            profile["pantry"] = [row["name"] for row in house]
            self._data["profile"] = self._normalize_profile(profile)
            await self._save()
            return {
                "profile": self.profile,
                "report": report,
                "restored": restored,
            }

    async def async_clear_pending_consumption(self, pending_id: str) -> bool:
        async with self._durable_mutation():
            pending = self._data.get("pendingConsumption")
            if not isinstance(pending, dict) or str(pending.get("id")) != str(pending_id):
                return False
            self._data["pendingConsumption"] = None
            await self._save()
            return True

    def user_ui_preferences(self, user_id: str) -> dict[str, Any]:
        return deepcopy(self._data.get("userUiPreferences", {}).get(user_id, {}))

    async def async_set_user_ui_preferences(self, user_id: str, preferences: dict[str, Any]) -> dict[str, Any]:
        from .shared_recipe_filters import merge_preferences
        async with self._durable_mutation():
            users = self._data.setdefault("userUiPreferences", {})
            users[user_id] = merge_preferences(users.get(user_id, {}), preferences)
            await self._save()
            return self.user_ui_preferences(user_id)

    async def async_set_ui_preferences(self, preferences: dict[str, Any]) -> dict[str, Any]:
        """Persist Recipe Hub display controls without touching dietary profile data."""
        async with self._durable_mutation():
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
        async with self._durable_mutation():
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
        async with self._durable_mutation():
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
        async with self._durable_mutation():
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
        profile["habitTerms"] = self._habit_terms()
        return profile

    def annotate(self, recipe: dict[str, Any], *, diet: str | None = None, diet_filters: dict | None = None) -> dict[str, Any]:
        result = deepcopy(recipe)
        house = self._data["profile"].get("houseIngredients")
        profile = self._scoring_profile()
        if diet in {"omnivore", "pescatarian", "vegetarian", "vegan"}:
            profile["diet"] = diet
        if diet_filters is not None:
            from .diet_profiles import scoring_profile
            profile = scoring_profile(profile, diet_filters)
        base_match = score_recipe(result, profile)
        match = enrich_match_with_house_keys(result, base_match, house)
        if match.get("safe"):
            quantity = recipe_quantity_feasibility(
                result,
                house,
                availability=match.get("ingredientAvailability"),
            )
            match["quantityCoverage"] = quantity["quantityCoverage"]
            match["quantityConfidence"] = quantity["confidence"]
            match["quantityAvailability"] = quantity["items"]
            match["quantityShortages"] = quantity["shortages"]
            match["quantityUnknown"] = quantity["unknown"]
            match["fullyAvailableByQuantity"] = quantity["fullyAvailable"]

            expiry = recipe_expiry_priority(
                result,
                house,
                today=dt_util.now().date(),
                within_days=DEFAULT_EXPIRY_WARNING_DAYS,
            )
            base_score = float(match.get("score") or 0.0)
            expiry_priority = float(expiry.get("priority") or 0.0)
            expiry_bonus = min(40.0, expiry_priority * 20.0)
            quantity_adjustment = -25.0 * max(0.0, 1.0 - float(quantity["quantityCoverage"]))
            match["baseScore"] = round(base_score, 1)
            match["expiryPriority"] = round(expiry_priority, 3)
            match["expiryBonus"] = round(expiry_bonus, 1)
            match["expiringIngredients"] = expiry.get("ingredients") or []
            match["quantityScoreAdjustment"] = round(quantity_adjustment, 1)
            match["score"] = round(base_score + expiry_bonus + quantity_adjustment, 1)
        result["match"] = match
        return result

    def rank(self, recipes: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
        from .recipe_suitability import meal_candidates
        scored = [self.annotate(x) for x in meal_candidates(recipes)]
        safe = [x for x in scored if x.get("match", {}).get("safe") or x.get("match", {}).get("eligibleWithSubstitutions")]
        safe.sort(key=lambda x: x.get("match", {}).get("score", -1000), reverse=True)
        return safe[: max(1, min(int(limit), 50))]
