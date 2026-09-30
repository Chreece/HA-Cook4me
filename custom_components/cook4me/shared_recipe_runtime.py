"""Bind the shared filter contract to stored inventory, costs and history."""
from .shared_recipe_filters import apply_filters, ingredient_aliases, normalize_filters


def _candidate_identity(row):
    """Stable recipe-family identity used only for shortlist rotation."""
    from .today_logic import recipe_identity
    if not isinstance(row, dict):
        return ""
    return str(row.get("displayFamilyId") or recipe_identity(row) or "").strip()


def compact_candidate_history(previous, rows, maximum=12000):
    """Keep oldest->newest unique family IDs so the whole catalog can rotate."""
    ordered = []
    seen = set()
    for value in list(previous or []) + [
        _candidate_identity(row) for row in rows if isinstance(row, dict)
    ]:
        value = str(value or "").strip()
        if not value:
            continue
        if value in seen:
            ordered = [item for item in ordered if item != value]
        else:
            seen.add(value)
        ordered.append(value)
    return ordered[-max(1, int(maximum)):]


def _bounded_suggestion_candidates(
    rows,
    settings,
    languages,
    limit,
    candidate_history=None,
):
    """Rotate a diverse exact-nutrition shortlist across every eligible recipe."""
    from .today_logic import recipe_matches_meal_types

    try:
        maximum = max(1, int(limit))
    except (TypeError, ValueError):
        return rows
    if len(rows) <= maximum:
        return rows

    meal_types = [
        str(value)
        for value in (settings.get("mealTypes") or [])
        if str(value)
    ]
    catalogs = []
    for value in languages or []:
        code = str(value or "").strip().lower().replace("_", "-").split("-", 1)[0]
        if code and code not in catalogs:
            catalogs.append(code)

    # candidate_history is oldest -> newest. Recipes never exact-scored before
    # come first; once all eligible families have been visited, the oldest exact
    # candidates rotate back in. Existing score order breaks ties, preserving
    # quality while ensuring the bounded window eventually traverses the entire
    # eligible catalog instead of becoming a permanent top-192/top-180 pool.
    last_seen = {
        str(value): index
        for index, value in enumerate(candidate_history or [])
        if str(value)
    }
    source_order = {id(row): index for index, row in enumerate(rows)}

    def rotation_key(row):
        ident = _candidate_identity(row)
        return (
            1 if ident in last_seen else 0,
            last_seen.get(ident, -1),
            source_order[id(row)],
        )

    rotated = sorted(rows, key=rotation_key)
    chosen = []
    seen = set()

    def row_language(row):
        value = (
            row.get("todayCatalogLanguage")
            or row.get("catalogLanguage")
            or row.get("language")
            or ""
        )
        return str(value).strip().lower().replace("_", "-").split("-", 1)[0]

    def add(row):
        marker = id(row)
        if marker in seen or len(chosen) >= maximum:
            return False
        seen.add(marker)
        chosen.append(row)
        return True

    # First preserve one rotating candidate for every requested meal/catalog pair
    # that currently exists.
    if meal_types and catalogs:
        for meal_type in meal_types:
            for catalog in catalogs:
                for row in rotated:
                    if (
                        row_language(row) == catalog
                        and recipe_matches_meal_types(row, [meal_type])
                        and add(row)
                    ):
                        break
                if len(chosen) >= maximum:
                    return chosen

    # Reserve category coverage from the rotating order.
    if meal_types:
        meal_quota = max(4, min(24, maximum // max(1, len(meal_types) * 2)))
        for meal_type in meal_types:
            count = 0
            for row in rotated:
                if not recipe_matches_meal_types(row, [meal_type]):
                    continue
                if add(row):
                    count += 1
                if count >= meal_quota or len(chosen) >= maximum:
                    break

    # Reserve catalog-language coverage from the rotating order.
    if catalogs:
        language_quota = max(3, min(16, maximum // max(1, len(catalogs) * 4)))
        for catalog in catalogs:
            count = 0
            for row in rotated:
                if row_language(row) != catalog:
                    continue
                if add(row):
                    count += 1
                if count >= language_quota or len(chosen) >= maximum:
                    break

    for row in rotated:
        if len(chosen) >= maximum:
            break
        add(row)
    return chosen

def executor_progress(callback):
    """Marshal executor progress onto HA's event loop before firing events."""
    import asyncio
    from functools import partial
    loop = asyncio.get_running_loop()
    return lambda phase, **values: loop.call_soon_threadsafe(partial(callback, phase, **values))


async def search_filtered(
    bridge,
    *,
    query,
    languages,
    language,
    filters,
    progress=None,
    exact_nutrition_limit=None,
    candidate_history=None,
):
    from functools import partial
    from . import release_catalog
    from .websocket_v30 import _device_language, _device_country
    from .executor_progress import ExecutorProgress
    report = ExecutorProgress(progress)
    try:
        # Always supply checkpoints, including when there is no subscribed UI.
        process = await processor(
            bridge,
            filters,
            language=language,
            progress=report,
            for_suggestions=True,
            exact_nutrition_limit=exact_nutrition_limit,
            candidate_languages=languages,
            candidate_history=candidate_history,
        )
        return await report.run(bridge.hass, partial(
            release_catalog.search_release_recipes,
            query,
            language=language,
            configured_language=_device_language(bridge),
            country=_device_country(bridge),
            catalog_languages=languages,
            group_families=True,
            all_results=True,
            filter_rows=process,
            progress=report,
        ))
    finally:
        report.close()


async def processor(
    bridge,
    filters,
    *,
    language="en",
    rank=True,
    score_targets=True,
    progress=None,
    cost_calculator=None,
    for_suggestions=False,
    exact_nutrition_limit=None,
    candidate_languages=None,
    candidate_history=None,
):
    from . import websocket_v13 as v13
    from . import websocket_v18 as v18
    from .costs import cost_store_for_bridge
    from .costing import calculate_recipe_cost
    from .meal_history import meal_history_store_for_bridge
    from .nutrition import nutrition_store_for_bridge
    from .nutrition_fefo import calculate_recipe_nutrition_fefo
    from .today_logic import recipe_identity
    from .diet_profiles import resolve_filters
    settings = resolve_filters(bridge.recipe_hub.profile, normalize_filters(filters))
    house = bridge.recipe_hub.profile.get("houseIngredients") or []
    costs = await cost_store_for_bridge(bridge) if settings["maxCost"] is not None else None
    market = None
    if settings.get("seasonalIngredients") is True or (costs is not None and cost_calculator is None):
        from .automatic_prices import price_settings
        market = await price_settings(bridge)
    season_country, season_month = "", None
    if settings.get("seasonalIngredients") is True:
        from datetime import datetime
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        season_country = str((market or {}).get("country") or "").strip().upper()
        try:
            zone = ZoneInfo(str(getattr(bridge.hass.config, "time_zone", "") or "UTC"))
            season_month = datetime.now(zone).month
        except (TypeError, ValueError, ZoneInfoNotFoundError):
            season_month = datetime.now().month
    nutrients = await nutrition_store_for_bridge(bridge)
    history = await meal_history_store_for_bridge(bridge)
    recent = v18._recent_identities(
        history.recent(200),
        days=int(settings["avoidRecentDays"] or 0),
    )
    aliases = (
        await bridge.hass.async_add_executor_job(ingredient_aliases, language)
        if settings["ingredients"]
        else {}
    )
    if costs is not None and cost_calculator is None:
        from .automatic_prices import offline_price_inputs
        from .release_catalog import async_warm_release_catalog
        catalog = await async_warm_release_catalog(bridge.hass)
        lookup = {
            str(row[key]): row
            for row in catalog["ingredients"]
            for key in ("key", "foodKey", "id", "ingredientId")
            if row.get(key)
        }

        def cost_calculator(row):
            recipe, references = offline_price_inputs(
                row, [], costs, market, catalog_lookup=lookup
            )
            return calculate_recipe_cost(
                recipe,
                house,
                references,
                country=market["country"],
                currency=market["currency"],
            )

    def process(rows):
        if for_suggestions:
            from .recipe_suitability import meal_candidates
            rows = meal_candidates(rows)

        # These properties return deep copies. Snapshot once per pass, not twice
        # for every recipe in the catalog; the calculation does not mutate them.
        generic, stock_lots = nutrients.generic, nutrients.stock_lots
        rows = [row for row in rows if recipe_identity(row) not in recent]
        if rank or "dietProfile" in settings:
            rows = v13._rank_filtered(
                bridge,
                rows,
                diet=settings["diet"],
                limit=max(1, len(rows)),
                unlimited=True,
                diet_filters=settings if "dietProfile" in settings else None,
                for_suggestions=for_suggestions,
                progress=(
                    lambda done, total: progress(
                        "ranking", completed=done, total=total
                    )
                )
                if progress
                else None,
            )

        # Today/Week suggestion generation used to run exact FEFO nutrition for
        # every catalog recipe (9k+ on the full release). Apply every hard filter
        # first using already-compiled catalog nutrition, retain a diverse bounded
        # shortlist, and only then calculate user/inventory-specific nutrition.
        # Manual/official search keeps the historical unbounded behavior unless a
        # caller explicitly opts into this bound.
        if (
            exact_nutrition_limit is not None
            and for_suggestions
            and len(rows) > max(1, int(exact_nutrition_limit))
        ):
            prefilter_settings = dict(settings)
            # Expiry preference is a score adjustment, not an eligibility rule.
            # Keep the base score untouched until the final exact pass.
            prefilter_settings["preferExpiring"] = True
            rows = apply_filters(
                rows,
                prefilter_settings,
                ingredient_groups=aliases,
                cost=cost_calculator,
                nutrition=None,
                score_targets=False,
                progress=None,
                season_country=season_country,
                season_month=season_month,
            )
            rows = _bounded_suggestion_candidates(
                rows,
                settings,
                candidate_languages,
                exact_nutrition_limit,
                candidate_history=candidate_history,
            )
            # A max-cost prefilter has already attached the exact cost to each
            # surviving row, so the final pass can reuse it rather than calculate
            # the same price twice.
            final_cost_calculator = None
        else:
            final_cost_calculator = cost_calculator

        return apply_filters(
            rows,
            settings,
            ingredient_groups=aliases,
            cost=final_cost_calculator,
            nutrition=lambda row: calculate_recipe_nutrition_fefo(
                row,
                house,
                generic=generic,
                stock_lots=stock_lots,
            ),
            score_targets=score_targets,
            progress=progress,
            season_country=season_country, season_month=season_month,
        )
    return process
