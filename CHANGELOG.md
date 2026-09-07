# Changelog

## 2026.9.7.2

- Add a consolidated Home Assistant persistent notification for house-stock ingredients whose **best-before date is today, within the next 3 days, or already past**. The notification is created immediately on startup or stock changes and refreshed every day at 09:00 Home Assistant local time.
- Refresh/dismiss the best-before notification immediately after manual inventory changes, barcode stock additions and confirmed recipe consumption so it never waits for the next daily check when stock changes.
- Keep expired/past-best-before items visible in the notification, but deliberately do **not** promote them as cooking suggestions; recipe priority applies only from today through the 3-day warning horizon.
- Give **For what I have in my house** recipes an expiry-aware ranking bonus when they use soon-expiring stock, while retaining pantry coverage/diet/allergy safety as the main suitability score. One urgent ingredient can move a similarly suitable recipe upward; poor pantry matches do not automatically beat recipes the user can actually make.
- Attach `expiryPriority`, `expiryBonus`, `expiringIngredients` and the pre-expiry `baseScore` to recommendation match metadata for transparent/debuggable ranking.
- When the recommendation query is empty, augment the normal vendor top-result set with small searches for up to the three most urgent ingredients before ranking. This prevents expiring ingredients from receiving no benefit merely because no matching recipe happened to be present in the generic top-50 catalog page.
- Apply the same expiry bonus in the reusable Recipe Hub ranking path used by Home Assistant services, not only the sidebar WebSocket UI.
- Add deterministic tests for the 3-day warning window, past-date handling, unlimited stock with dates, and stable `M_FOOD_*` expiry matching.

## 2026.9.7.1

- Add an optional **Best before** date to every house-stock ingredient, including unlimited (`∞`) stock.
- Preserve and normalize the date as ISO `YYYY-MM-DD`, allow it to be edited or cleared later, and show it alongside the stored amount in the house inventory.
- When the same ingredient is restocked, keep the **earliest known best-before date** while combining compatible quantities so the inventory remains conservative about what should be used first.
- Add Best-before input to manual catalog additions and one-time barcode-to-Cook4Me mapping without persisting package-specific dates in the barcode mapping itself, because two packages with the same EAN can have different dates.
- Carry the stock best-before date into post-recipe consumption confirmation metadata and preserve it while quantities are deducted.
- Ship/cache-bust Recipe Hub v20 and add inventory regressions for finite/unlimited dates, restocking, editing/clearing, invalid date rejection and consumption metadata.

## 2026.9.6.22

- Replace the barcode mapping form's WebView-dependent `datalist` text field with a real searchable Cook4Me ingredient picker. Likely matches are shown first and the user can search/select from the cached full ingredient catalog on mobile and desktop.
- Load the ingredient catalog on demand when a scanned product needs mapping, so the mapping selector does not appear empty merely because the profile catalog had not finished loading yet.
- Keep catalog identity intact when a user confirms a mapping: the selected SEB `M_FOOD_*` key and canonical catalog name are stored instead of accepting arbitrary free text.
- Add a conservative language-neutral near-token suggestion path for small word-ending variations such as German `Datteln` → `Dattel`. These fuzzy candidates are suggestion-only and never cross the automatic-mapping confidence threshold.
- Preserve exact/high-confidence automatic mapping for products that genuinely match the catalog, and keep manual confirmation for ambiguous products.
- Ship and cache-bust Recipe Hub v19 and validate the new picker plus barcode matching regression in CI.

## 2026.9.6.21

- Use the Home Assistant Android Companion app's native barcode-scanner capability when `hasBarCodeScanner` is advertised, instead of relying on WebView camera / `BarcodeDetector` support.
- Open the native scanner through the Home Assistant external bus (`bar_code/scan`) and accept physical shopping formats `EAN-13`, `EAN-8`, `UPC-A`, `UPC-E` and `ITF`; unsupported code types are rejected without sending them to product lookup.
- Keep the existing browser `BarcodeDetector` + rear-camera scanner unchanged as the fallback outside the Companion app.
- Observe only the native scanner request created by Cook4Me while leaving Home Assistant's normal external-message handler in place to acknowledge and process every command.
- Keep the native scanner open after known-product scans for rapid multi-product shopping intake. When an unknown product needs its one-time Cook4Me mapping, temporarily close the native overlay, show the editable mapping form, then reopen the native scanner automatically after saving the mapping.
- Ship and cache-bust Recipe Hub v18 and validate its frontend syntax in CI.

## 2026.9.6.20

- Add **Scan shopping** to **House ingredients & diet** for physically scanning EAN/UPC product barcodes with the phone/rear camera while keeping the scanner open between products.
- Use the browser Barcode Detection API when available for `EAN-13`, `EAN-8`, `UPC-A`, `UPC-E` and ITF-compatible scans, with a manual barcode field retained as a fallback when the current browser cannot expose live barcode detection/camera access.
- Resolve scanned barcodes through the current Open Food Facts product API and read product name, generic name, brand and package quantity/unit when available.
- Match product metadata against the cleaned Cook4Me ingredient catalog conservatively. Exact/high-confidence generic/product-name matches are automatically mapped and immediately added to house stock.
- Never silently guess weak matches. Unknown or ambiguous products open a one-time mapping form where the user selects the Cook4Me ingredient and edits the package amount/unit.
- Persist barcode-to-ingredient/package mappings per Cook4Me config entry. After the first confirmed mapping, every future scan of that barcode automatically adds the remembered package amount to the existing stock.
- Repeated scans of the same product add repeated packages, so scanning two 500 g packages increases the same stable ingredient stock by another 1 kg through the existing unit-safe inventory contract.
- Keep stable SEB `M_FOOD_*` ingredient identity in remembered mappings so barcode-stock additions participate in recipe availability/missing-ingredient/shopping-list decisions exactly like manually selected house stock.
- Add Recipe Hub v17, v15 barcode WebSocket APIs and focused tests for barcode validation, multi-pack quantity parsing, Open Food Facts normalization and conservative catalog matching.

## 2026.9.6.19

- Turn **What I have in my house** into quantity-aware stock. Each ingredient can store an amount and unit, or be marked **unlimited (∞)** for things such as water.
- Restocking an ingredient that is already present increases its existing amount instead of creating a duplicate. Safe language-neutral conversions are supported for mass (`mg/g/kg`), volume (`µl/ml/cl/dl/l`) and explicit count units; unknown/localized units are only combined when their unit token actually matches, never guessed.
- Keep ingredient identity based on the stable SEB `M_FOOD_*` key whenever available, so stock quantities do not break recipe matching even when recipe wording contains quantities/preparation notes or a different localized display label.
- Replace the home-ingredient chips with a collapsible editable stock list. Stored quantities are shown in parentheses, can be edited later, and depleted finite stock is removed automatically.
- Keep the ingredient catalog at its current scroll position after **Add to house stock**. The catalog is no longer rerendered on every stock addition, and already-owned ingredients remain selectable so purchases can be added to their existing totals.
- Detect recipe completion only on the explicit normalized cooker `phase=done` transition; recipe unload/idle alone is not treated as successful completion.
- After a positively detected completion, create a Home Assistant persistent notification and a pending Cook4Me consumption confirmation. Each tracked recipe ingredient defaults to **Consumed = Yes** and to the exact quantity/unit required by the recipe; every amount remains editable before confirmation.
- Confirmation deducts each approved ingredient from house stock, converts compatible units safely, removes stock that reaches zero, and never reduces unlimited ingredients. Users can also confirm that nothing was consumed.
- Persist pending consumption confirmation across Home Assistant restarts and dismiss the associated persistent notification after confirmation/cancellation.
- Add Recipe Hub v16 plus v14 inventory/consumption WebSocket APIs and regression tests for restocking, stable-key recipe matching, unit conversion, depletion, and unlimited stock.

## 2026.9.6.18

- Harden the recipe-derived ingredient catalog around **SEB food identity** instead of language-specific text cleanup. Official recipe rows are admitted only when SEB supplies a stable `foodKey` or at least a canonical `foodName`; keyless free-form recipe prose is excluded from the ingredient selector.
- Group every occurrence of the same `M_FOOD_*` key and choose one least recipe-specific label, preferring canonical `foodName` whenever present. This collapses preparation/serving variants such as parenthetical quantities and comma-delimited preparation notes without maintaining per-language word lists.
- Drop cookware, paper, molds, serving dishes and other non-food recipe-description rows structurally because they have no proven SEB food identity, rather than trying to recognize those objects by translated names.
- Make ingredient-name normalization Unicode-safe for Latin, Cyrillic, Arabic, CJK and the rest of the 21 source catalogs; deduplication no longer relies on ASCII-only normalization.
- Keep the dedicated SEB `marketingFoods` endpoint trusted as a food catalog, while applying the conservative identity gate only to the recipe-derived fallback.
- Perform final backend deduplication on the cleaned visible ingredient name as well as food identity, preferring a row that preserves a stable SEB key.
- Version the recipe-derived ingredient cache to `v3_food_identity`; older fallback catalogs are invalidated and rebuilt immediately instead of retaining already-flattened polluted labels for 24 hours.
- Add regressions for amount cleanup, Unicode normalization, keyless-prose rejection, cross-occurrence canonicalization and post-cleanup duplicate removal.

## 2026.9.6.17

- Remove the ingredient-catalog editor from **For what I have in my house**. Ingredient selection now lives only under **House ingredients & diet**.
- Make the recommendation tab a filter/results view: optional recipe text query (for example `risotto`), optional transient diet filter, recipe language/translation controls, and the recipe results grid.
- Send the recipe text filter to the real SEB catalog search instead of filtering only the already-loaded cards locally.
- Keep the saved house ingredients active automatically for availability scoring/ranking, together with saved allergy/avoid rules and learned preference hints.
- A transient diet choice affects only the current recommendation request; **Profile diet** keeps the saved profile diet without modifying it.
- Expand recommendation sampling to up to 50 matching catalog recipes and return up to 24 ranked results.
- Ship Recipe Hub v15 plus the v13 filtered-recommendation WebSocket API and regression checks that the recommendation tab contains no house-catalog editor.

## 2026.9.6.16

- Remove the accidental frontend truncation of the ingredient catalog. The recommendation editor no longer stops after the first 150 sorted entries, and the profile editor no longer stops after 100; both now expose the full cleaned cached catalog (up to the backend 5,000-item bound) and search across all of it.
- Ship and cache-bust Recipe Hub v14 and validate its JavaScript syntax in CI.

## 2026.9.6.15

- Remove the obsolete “one ingredient per line” notice from the recommendation UI.
- Add a final visual-name deduplication pass after quantity/unit cleanup so identical cleaned ingredient names are shown only once, preferring a row with a stable SEB `M_FOOD_*` key when available.

## 2026.9.6.14

- Put the **What I have in my house** ingredient-catalog editor directly on the recommendation tab, so users can search/select/remove house ingredients where those ingredients are actually used. Changes are saved immediately and invalidate stale recommendation results.
- Add a dedicated **Shopping list** Recipe Hub tab backed by Home Assistant's native Shopping List / `todo` entity. It shows active/completed items and supports add, complete/uncomplete, remove, refresh, and clear-completed actions without creating a second Cook4Me-specific list.
- Keep the existing per-recipe and per-ingredient **Add to Shopping List** buttons wired to that same native list.
- Remove recipe-specific quantities and units from the ingredient-selection catalog. The cleaner prefers SEB canonical food names, otherwise removes structured `quantity` + `unit` prefixes without relying on language-specific words, with Unicode numeric/fraction fallback for partial publications.
- Cover decimal commas, Unicode vulgar fractions, Arabic-Indic digits, unitless quantities and localized units, with regressions across German, French, Spanish, Arabic and Japanese examples.
- Version recipe-derived ingredient-cache entries and invalidate the old v11 fallback cache immediately, so amount-polluted rows are rebuilt on first use instead of surviving the 24-hour TTL.
- Ship Recipe Hub v12 frontend/backend APIs and validate the v12 frontend in CI.

## 2026.9.6.13

- Restrict the explicit official **Recipe language** selector to the 21 source catalogs proven by the standalone v2 audit: `ar`, `bg`, `cs`, `de`, `en`, `es`, `fr`, `hr`, `hu`, `it`, `ja`, `ko`, `pl`, `pt`, `ro`, `ru`, `sk`, `sl`, `tr`, `uk`, `zh`. Greek and other unsupported source catalogs remain valid Home Assistant UI / AI translation targets but are no longer presented as official SEB source catalogs.
- Make **Automatic** recipe-catalog language resolve from the Cook4Me setup/device language instead of the Home Assistant UI language. AI Task translation remains independently targeted at the Home Assistant language.
- Replace the free-text fridge/pantry concept with structured **What I have in my house** inventory. House ingredients retain stable SEB `M_FOOD_*` keys when available, so availability matching survives switching catalog display languages.
- Add a per-language ingredient catalog with a persistent **24-hour cache**. The integration first tries the APK-proven `common-api/datarefs/marketingFoods/search` route using only its proven query parameters and an empty/default body; because the exact `th0.d` request body remains unrecovered, rejection safely falls back to a bounded crawl of hydrated official recipe ingredients rather than inventing body fields.
- Keep compatibility with existing profiles by migrating the previous `pantry` string list into structured house ingredients and mirroring their display names back to `pantry` for older ranking/AI code.
- Show each recipe ingredient as **At home**, **Basic staple**, or **Missing**. Stable food keys take precedence over localized text when determining whether an ingredient is already in the house.
- Integrate missing ingredients with Home Assistant's native **Shopping List**. Every missing ingredient can be added individually, and every recipe/card can add all missing ingredients at once. Existing shopping-list entries are skipped when the native todo list can be read.
- Fix stale SEB search publications (observed in Spanish and Portuguese): dead/404 recipe IDs no longer occupy result slots. The hydrator keeps advancing through source pages until the requested number of valid grouped recipes is filled or the catalog is exhausted.
- Add Recipe Hub v11 APIs/UI, cache-bust the panel, and extend CI frontend validation to the v11 module.

## 2026.9.6.12

- Replace the active Recipe Hub search body with the **standalone-proven Cookeo/KRUPS contract**. The exact request uses `lang.key`, `market.key`, `applianceGroups.reference.key=APPLIANCE_GROUP_15` and `topRecipe.type.key=BRAND` with `groupBy=""`.
- Remove the speculative v8 `fieldList`, `FOOD_COOKING`, privacy/source and empty-filter-list body members from the active search path.
- Preserve the proven `/common-api/v4/search/recipes` endpoint and its normal query parameters.
- Add a regression from the real standalone proof: **29 German serving variants collapse by `groupingId` to exactly 11 logical recipes**, including `Pfifferling-Risotto`, `Risotto "Aus Vorräten"` and `Risotto mit roten Linsen`.
- Selectively invalidate only pre-proof persistent **search** cache entries while keeping persistent UI preferences, hydrated detail cache and AI-translation cache intact.
- Keep one-card-per-recipe grouping, per-language/per-serving selectors, default-AI-Task translation rules and device-locale send identity unchanged.
- Cache-bust the Recipe Hub panel URL for the v12 upgrade.

## 2026.9.6.11

- Fix the v10 diagnostic path so recipe catalog authentication refresh stays on the v9 **KRUPS HTTP-only** flow and never starts an unrelated MQTT status request when the cooker is offline.
- Add a regression preventing the diagnostic wrapper from routing back through the old MQTT-dependent search/auth path.

## 2026.9.6.10

- Add a redacted, read-only A/B diagnostic for rejected recipe searches so legacy-body success can be distinguished from request-body rejection or real credential/context failure.
- Keep tokens/passwords/credentials out of diagnostics and UI errors.
- Add a temporary compatibility fallback only when the diagnostic proves the legacy search body is accepted while the newer reconstructed body is rejected.

## 2026.9.6.9

- Refresh recipe-catalog authentication with browserless KRUPS HTTP login only; do not require an AWS IoT/MQTT round-trip for ordinary recipe search/detail operations.
- Preserve the live search draft independently from the last submitted query so changing language/translation/tab controls no longer clears text being typed.
- Persist the search draft with the rest of the Recipe Hub preferences.

## 2026.9.6.8

- Persist Recipe Hub UI preferences in Home Assistant storage: global recipe-language mode, translation toggle, last tab, per-recipe source-language choice, and per-recipe serving choice now survive panel reloads and Home Assistant restarts.
- Replace the active official-search request body with the current APK `SearchRecipesV2` contract instead of sending an empty JSON object. The v8 request repeats `lang`/`market` as the app's field filters and includes the app-observed privacy/source-system/food-cooking constraints plus its requested field list.
- Keep the proven `/common-api/v4/search/recipes` endpoint and `q` query parameter; the change is the missing app search context/body, not an invented replacement catalog.
- Continue hydrating recipe details before render, then group only after exact recipe metadata is available.
- Merge same-language serving publications with an exact same title + exact recipe cover fallback even when SEB published their serving variants under different top/grouping IDs. This fixes repeated identical cards such as 2/4/6-serving versions of one recipe.
- Represent a logical recipe as **language variants → serving variants**. Recipes sharing a proven SEB grouping ID across languages are rendered once and expose a per-card/per-detail language selector; each selected language then exposes only its own available serving variants.
- Keep appliance delivery identity separate from display language: each displayed serving is paired only with an exact same-serving device-locale variant. A display variant without a proven device serving variant remains viewable but not sendable.
- Preserve the existing persistent search/detail/AI-translation cache from v7; v8 search cache keys include the new APK search-contract revision so stale empty-body results are not reused.
- Add regressions for APK search-body fields, persistent UI preferences, exact 2/4/6 serving collapse, and same-group language menus with independent serving lists.
- Ship cache-busted Recipe Hub v8 frontend/backend APIs.

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
- Ship a cache-busted Recipe Hub v7 frontend/backend APIs and validate Python, tests, JSON, HACS and frontend syntax in CI.

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
- Recipe Hub dashboard for official search, fridge/pantry recommendations, manual cook-along recipes and AI-assisted cook-along recipes.
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
- Added state-aware official recipe delivery through the proven Cook4Me AWS IoT shadow route.
- Added state-aware send guard when another recipe/session is loaded.
- Added profile hard gate for diet/allergy/avoid restrictions on every official send path.
- Added pantry/fridge matching and missing-ingredient ranking.
- Added persistent manual recipe library and cook-along view.
- Added Home Assistant Conversation-agent recipe generation.
- Added deterministic backend validation of AI recipes before save.
- Added a default merged State summary sensor; legacy granular sensors remain compatible and default-disabled for new registrations.
- Disabled the Updating binary sensor by default for new registrations.
- Added WebSocket APIs for panel overview/search/detail/recommend/send/profile/recipe storage.
- Added `search_recipes` and `recommend_recipes` services with response data.
- Added 15-minute recipe-search cache and concurrent detail enrichment (max 4 workers).
- Removed a historical hardcoded appliance UUID from the vendor client's default values; config-entry UUID remains injected dynamically.
