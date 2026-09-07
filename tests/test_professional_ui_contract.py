from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v32.js"
HOTFIX_JS = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v33.js"
TODAY_JS = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v34.js"
INLINE_FIX_JS = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v35.js"
COMPACT_JS = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v36.js"
RESPONSIVE_JS = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v37.js"
RESTORE_JS = ROOT / "custom_components" / "cook4me" / "frontend" / "cook4me-panel-v38.js"
WS12 = ROOT / "custom_components" / "cook4me" / "websocket_v12.py"
WS19 = ROOT / "custom_components" / "cook4me" / "websocket_v19.py"
PANEL = ROOT / "custom_components" / "cook4me" / "panel.py"
MANIFEST = ROOT / "custom_components" / "cook4me" / "manifest.json"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_professional_ui_visual_language_contract():
    text = _text(JS)
    assert 'COUNTRY_BY_LANGUAGE' in text
    assert 'MEAL_VISUALS' in text
    assert 'rx-language-choice' in text
    assert 'rx-meal-choice' in text
    assert 'rx-nutrition-chip' in text
    assert 'details.rx-advanced' in text
    assert 'rx-plan-summary' in text
    assert 'ha-icon icon="mdi:' in text


def test_background_job_cards_and_cancellation_contract():
    text = _text(JS)
    assert 'cook4meJobStack' in text
    assert 'rx-job-card' in text
    assert '_processStart(title,detail="",options={})' in text
    assert 'token.cancelled=true' in text
    assert 'jobCancelRequested' in text
    assert '_hydrateVisibleNutrition(items)' in text
    assert 'while(cursor<rows.length&&!job.cancelled)' in text
    for name in (
        '_loadIngredientCatalog',
        '_loadNutritionSettings',
        '_loadTodayOptions',
        '_loadBookState',
        '_ensureScanCatalog',
        '_handleBarcode',
        '_openLocal',
        '_selectRecipeLanguage',
        '_selectServing',
    ):
        assert name in text


def test_v33_disables_self_triggering_subtree_observer():
    text = _text(HOTFIX_JS)
    assert '_installModernObserver()' in text
    assert 'this._modernObserver?.disconnect()' in text
    assert 'this._modernObserver=null' in text
    assert 'new MutationObserver' not in text
    assert 'if(option.textContent!==next)option.textContent=next' in text
    assert 'if(target.innerHTML!==next)' in text


def test_v34_today_is_one_recipe_per_selected_category():
    text = _text(TODAY_JS)
    assert 'TODAY_MEAL_TYPES=["breakfast","starter","salad","soup","main","side","dessert","snack"]' in text
    assert 'mealTypes:[...TODAY_MEAL_TYPES]' in text
    assert 'meal_count:8' in text
    assert 'for(const category of s.mealTypes)' in text
    assert 'picked.todayMealType=category' in text
    assert 'id="todayQuery"' not in text
    assert 'id="todayMealCount"' not in text


def test_v34_today_uses_catalog_ingredient_multiselect_and_bulk_controls():
    text = _text(TODAY_JS)
    assert 'id="todayIngredients" multiple' in text
    assert 'data-today-bulk="${group}"' in text
    assert '_toggleTodayBulk(c,group)' in text
    assert 'group==="ingredients"' in text
    assert 'group==="meals"' in text
    assert '[data-today-language]' in text
    assert '_recipeHasTodayIngredients' in text


def test_v34_recipe_cards_expand_steps_inline_and_toggle_closed():
    text = _text(TODAY_JS)
    assert 'rx-inline-expansion' in text
    assert '_toggleInlineRecipe(card,recipe,custom)' in text
    assert 'this._inlineRecipeKey===key&&card.classList.contains("rx-inline-expanded")' in text
    assert 'event.stopImmediatePropagation()' in text
    assert 'data-inline-ingredient' in text


def test_v35_expands_card_as_left_recipe_plus_right_steps_column():
    text = _text(INLINE_FIX_JS)
    assert 'grid-column:span 2!important' in text
    assert 'grid-template-columns:minmax(0,1fr) minmax(0,1fr)!important' in text
    assert 'rx-inline-left' in text
    assert 'grid-column:2!important' in text
    assert '_wrapInlineLeft(card)' in text
    assert 'card.querySelector(":scope > .rx-inline-expansion")?.remove()' in text


def test_v35_uses_original_seb_cover_instead_of_thumbnail():
    text = _text(INLINE_FIX_JS)
    assert '"/statics/thumb/","/statics/original/"' in text
    assert '_highResCover(value)' in text
    assert '_mediaHtml(recipe)' in text
    assert '_detailHtml(recipe)' in text


def test_v36_steps_button_uses_split_inline_panel():
    text = _text(COMPACT_JS)
    assert 'const open=inheritedOpen.cloneNode(true)' in text
    assert 'inheritedOpen.replaceWith(open)' in text
    assert 'this._toggleInlineRecipe(card,recipe,custom)' in text
    assert 'rx-category-result-expanded' in text
    assert 'grid-column:span 2!important' in text


def test_v36_shopping_list_has_select_and_deselect_all():
    frontend = _text(COMPACT_JS)
    backend = _text(WS12)
    assert 'button.id="shoppingToggleAll"' in frontend
    assert 'allCompleted?"incomplete_all":"complete_all"' in frontend
    assert '"complete_all"' in backend
    assert '"incomplete_all"' in backend
    assert 'target_status = "completed" if action == "complete_all" else "needs_action"' in backend


def test_v36_loaded_recipe_replacement_is_precook_only_and_verified():
    frontend = _text(COMPACT_JS)
    backend = _text(WS12)
    assert 'REPLACEABLE_PHASES=new Set(["idle","stopped","preparation","add_ingredient","done"])' in frontend
    assert 'cook4me/v12/send_recipe_replaceable' in frontend
    assert '_REPLACEABLE_RECIPE_PHASES = {"idle", "stopped", "preparation", "add_ingredient", "done"}' in backend
    assert 'phase not in _REPLACEABLE_RECIPE_PHASES' in backend
    assert '_wait_for_loaded_variant' in backend
    assert 'kept the previously loaded recipe' in backend
    assert 'bridge._run_client_json("state", timeout=35)' in backend


def test_v19_broadens_restricted_diet_catalog_before_rotation():
    text = _text(WS19)
    assert '_RESTRICTED_DIETS = {"vegetarian", "vegan", "pescatarian"}' in text
    assert 'return 8 if restricted else 4' in text
    assert 'return 5 if restricted else 3' in text
    assert 'for page in range(max(1, int(page_count)))' in text
    assert 'page=page' in text
    assert 'v13._dedupe_recipes(candidates)' in text
    assert 'catalogPagesRequested' in text
    assert 'select_diverse(' in text


def test_v38_uses_stable_v36_runtime_path_but_keeps_v19_today_backend():
    text = _text(RESTORE_JS)
    assert 'import "./cook4me-panel-v36.js"' in text
    assert 'customElements.get("cook4me-recipe-hub-panel-v36")' in text
    assert 'type==="cook4me/v18/today_suggest"?"cook4me/v19/today_suggest":type' in text
    assert 'cook4me-panel-v37.js' not in text


def test_v38_today_wraps_inside_page_without_horizontal_strip():
    text = _text(RESTORE_JS)
    assert 'grid-template-columns:repeat(auto-fit,minmax(145px,1fr))!important' in text
    assert '.rx-today-row{' in text
    assert 'overflow:visible!important' in text
    assert '@media(max-width:680px)' in text
    assert 'grid-template-columns:repeat(2,minmax(0,1fr))!important' in text
    assert '.rx-today-planner .rx-plan-summary{display:none!important}' in text
    assert 'queueMicrotask(cleanup)' in text


def test_v38_top_controls_are_unified_and_icon_only_without_replacing_language_select():
    text = _text(RESTORE_JS)
    assert 'rx-v38-top' in text
    assert 'const toolbar=refresh?.closest(".toolbar")' in text
    assert 'toolbar.insertBefore(control,refresh)' in text
    assert 'control.classList.add("rx-v38-globe")' in text
    assert 'icon.setAttribute("icon","mdi:web")' in text
    assert 'refresh.classList.add("rx-v38-refresh")' in text
    assert 'icon.setAttribute("icon","mdi:refresh")' in text
    assert 'refresh.replaceChildren(icon)' in text
    assert 'control.replaceChildren' not in text


def test_v38_is_active_and_versioned():
    panel = _text(PANEL)
    manifest = _text(MANIFEST)
    assert 'cook4me-recipe-hub-panel-v38' in panel
    assert 'cook4me-panel-v38.js' in panel
    assert '?v=2026.9.7.17' in panel
    assert '"version": "2026.9.7.17"' in manifest
