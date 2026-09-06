# Changelog

## 2026.9.6.7

- Rework official-search loading so Recipe Hub returns **fully hydrated recipe objects before the first render**. Cards no longer appear first as numeric IDs/no-photo placeholders and then mutate only after opening Steps.
- Perform deduplication only after detail hydration has exposed the proven SEB `groupingId`, so the same recipe is shown once even when the search endpoint returned separate 2/4/6-serving variants.
- Preserve those serving variants as a **servings selector** on the single recipe card/detail instead of duplicate cards. Selecting a serving loads the corresponding display variant and sends the corresponding device-locale official variant.
- Replace the v6 lightweight device/display merge in the active panel with a fully hydrated merge. Explicit German (`de` / `GS_DE`) search is therefore filtered after real recipe detail has established its language instead of filtering ID-only rows.
- Automatic/Home-Assistant-language mode uses a real target-language sibling when one exists; otherwise it falls back to the fully hydrated Cook4Me/device-locale recipe, never an arbitrary foreign sibling.
- Translation now runs only after recipes are fully hydrated, including their steps. The list is rendered after translation completes when translation is enabled, so opening Steps cannot leave the selected recipe untranslated while only the cards change.
- Add a persistent Home Assistant `Store` cache for normalized **search results, recipe details and AI Task translations**. Search cache is locale/query aware; detail cache is locale/variant aware; translation cache is keyed by source-content hash + target language.
- Cached translations survive panel reloads and Home Assistant restarts; changing serving quantities or source recipe text creates a different translation key rather than reusing incompatible text.
- Cache entries are bounded and time-limited, and explicit refresh bypasses cached search/detail data.
- Add regressions for one-card-per-grouping behavior, 2/4/6 serving preservation, strict German hydrated results, target-language/device-language fallback, and display/send serving-variant pairing.
- Ship cache-busted Recipe Hub v7 frontend/backend APIs and validate Python, tests, JSON, HACS and frontend syntax in CI.

## 2026.9.6.6

- When an exact selected/HA-language SEB sibling is unavailable, prefer the configured Cook4Me/device-locale recipe as the original-language fallback instead of an arbitrary foreign sibling returned by the display market.
- Hydrate ID-only fallback cards on demand using the fallback recipe's own source language, so “leave as-is” shows the real title/photo/ingredients/steps instead of numeric IDs such as `913005`.
- Hydration runs only for missing/numeric titles and in batches of four, avoiding unnecessary detail requests when the display catalog already supplied usable content.
- Preserve device-send IDs, profile scoring and availability state while hydrating display content.
- If a default AI Task exists and translation is enabled, hydrated source-language content is translated afterward; otherwise it remains untouched.
- Add a regression ensuring a foreign sibling from the requested market cannot override the device-language fallback when it is not actually in the target language.
- Ship a cache-busted Recipe Hub v6 frontend and validate it in CI.

## 2026.9.6.5

- Add a Recipe Hub **recipe-language selector** with Auto/Home Assistant plus the SEB/KRUPS catalog languages observed by the integration (including Greek, German, English, Slovak, Hungarian, Czech, Portuguese and others).
- A specifically selected language is a strict filter: recipes that are not actually returned in that language are omitted instead of silently falling back to another language.
- Keep **Automatic** mode tied to the Home Assistant UI language while preserving the separate Cook4Me/device-locale send variant.
- Replace the v4 Conversation-agent translation heuristic with Home Assistant's native **default AI Task** contract. Translation uses the preferred `gen_data_entity_id` through `ai_task.generate_data` semantics and never guesses a Conversation agent.
- Show/enable the **Translate results to Home Assistant language** toggle only when a usable preferred/default AI Task exists.
- If no default AI Task exists, do not show an error banner and do not modify recipe text: the original SEB/KRUPS language is displayed as-is.
- AI Task translation remains display-only; grouping IDs, recipe IDs, send variants and Cook4Me commands are never translated or modified.
- Translation provider/task failures are non-fatal and leave the original recipe visible.
- Add Recipe Hub v5 WebSocket APIs for capabilities, language-filtered search/detail/recommendations, and optional default-AI-Task translation.
- Add catalog-language regressions and validate the v5 frontend with Node syntax checks.

## 2026.9.6.4

- Decouple Recipe Hub **display locale** from the Cook4Me/device account locale. A Greek Home Assistant UI now searches the SEB Greek display catalog (`el` / `GS_GR`) while the device-side recipe lookup remains on its configured locale (for example `de` / `GS_DE`).
- Merge display and device catalog results by the proven SEB `groupingId`: localized title/photo/ingredients/steps come from the display sibling, while recipe delivery keeps the device-compatible variant IDs.
- Keep display-only localized recipes visible but conservatively disable sending until a matching device-market sibling is proven.
- Mark recipes with no official SEB sibling in the Home Assistant UI language as requiring translation instead of silently presenting foreign content as localized.
- Add automatic Home Assistant Conversation AI translation fallback for card titles/ingredients and full recipe steps when SEB does not provide the requested language.
- Translate in small batches and cache translations in the panel session; official SEB localization is always preferred over AI translation.
- Show the original source language when AI translation is used.
- Add localization regressions for Greek display-market selection, display/device grouping merge, device-send variant preservation, translation fallback markers, and display-only safety.
- Validate the Recipe Hub v4 frontend with Node syntax checks in CI.

## 2026.9.6.3

- Group official search results by the proven SEB `groupingId`, so serving/language variants no longer appear as duplicate recipe cards.
- Preserve a separate device-locale `sendVariantId` while preferring the Home Assistant UI language for the displayed sibling variant when the catalog returns one.
- Replace recursive media discovery with strict recipe-level `cover` / root `resourceMedias` extraction, preventing brand/partner/technique logos from being shown as recipe photos.
- Parse the real SEB step text fields `applicationDescription` and `applianceDescription`; automatic steps also retain program/type fallbacks instead of rendering empty numbered rows.
- Send the Home Assistant UI language with Recipe Hub search/detail/recommend requests and expose the source recipe language when an exact translation is unavailable.
- Use canonical ingredient names/quantities in cards and details instead of mixing full application descriptions with food names from another locale.
- Move recipe details above the result grid, preserve the search query while opening a recipe, auto-scroll the selected detail into view, and add a clear “Back to results” action.
- Add neutral cooker artwork when no valid recipe photo exists or an image fails to load.
- Add focused regressions for recipe grouping, device-vs-display variant selection, strict cover selection, and API step text extraction.
- Extend CI with JavaScript syntax validation for every shipped Recipe Hub frontend file.

## 2026.9.6.2

- Added a standard MIT `LICENSE` so the HACS repository license validation passes.
- Removed `zip_release` / `filename` from `hacs.json`; HACS now installs directly from the repository source when no GitHub Release asset exists, avoiding commit-SHA release-download 404 errors.
- Kept tagged GitHub Release packaging for future date.build releases, while making HACS installation independent of a release asset.

## 2026.9.6.1

- First HACS-ready `HA-Cook4me` repository release using `YYYY.M.D.BUILD` versioning.
- Recipe Hub dashboard for official search, fridge/pantry recommendations, manual cook-along recipes and AI-assisted recipes.
- Deterministic vegetarian/vegan/pescatarian/allergy/avoid safety gates.
- State-aware official recipe delivery through the proven Cook4Me AWS IoT shadow route.
- Consolidated State sensor with legacy granular entities retained for compatibility.
- Bundled Home Assistant 2026.3+ local icon/logo assets and dark-mode variants.
- HACS validation, source validation, automated release packaging and Dependabot workflows.

## Legacy development history

# Changelog

## 0.3.0

- Added Cook4Me Recipe Hub sidebar panel.
- Added official SEB recipe catalog search and enriched recipe detail retrieval.
- Added official recipe ingredient, exclusions, course, duration and yield metadata.
- Corrected recipe-send ID semantics to grouping functional ID + recipe functional ID.
- Added state-aware send guard when another recipe/session is loaded.
- Added profile hard gate for diet/allergy/avoid restrictions on every official send path.
- Added pantry/fridge matching and missing-ingredient ranking.
- Added omnivore, pescatarian, vegetarian and vegan modes.
- Added conservative multilingual allergy/category aliases and backend exclusion-key matching.
- Added ranking-only eating-habit affinity from repeated successful official sends.
- Added persistent manual recipe library and cook-along view.
- Added Home Assistant Conversation-agent recipe generation.
- Added deterministic backend validation of AI recipes before save.
- Added a default merged State summary sensor; legacy granular sensors remain compatible and default-disabled for new registrations.
- Disabled the Updating binary sensor by default for new registrations.
- Added WebSocket APIs for panel overview/search/detail/recommend/send/profile/recipe storage.
- Added `search_recipes` and `recommend_recipes` services with response data.
- Added 15-minute recipe-search cache and concurrent detail enrichment (max 4 workers).
- Removed a historical hardcoded appliance UUID from the vendor client's default values; config-entry UUID remains injected dynamically.
