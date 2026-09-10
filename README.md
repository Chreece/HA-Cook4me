# HA-Cook4me — Recipe Hub

💙 **Enjoying this hobby project? [Send a voluntary thank-you via Ko-fi](https://ko-fi.com/chreece).**

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
![Version](https://img.shields.io/badge/version-2026.9.6.12-blue.svg)

**Current version:** `2026.9.6.12` · version format: `YYYY.M.D.BUILD`

Home Assistant custom integration for KRUPS/Tefal **Cook4Me / Cookeo** Wi-Fi cookers, with cloud-push state, a Recipe Hub, official recipe delivery, pantry-aware recommendations, diet/allergy filtering, manual cook-along recipes and Home Assistant AI features.

> This project is independent and is not affiliated with or endorsed by Groupe SEB, KRUPS or Tefal. Product names are used only to describe compatibility.

## Install with HACS

1. HACS → Integrations → ⋮ → **Custom repositories**.
2. Add `https://github.com/Chreece/HA-Cook4me` as **Integration**.
3. Install **HA-Cook4me** and restart Home Assistant.
4. Settings → Devices & services → **Add integration** → HA-Cook4me.

HACS installs directly from the repository source, so installation does not depend on a GitHub Release ZIP being present for every commit. Tagged releases can still provide `HA-Cook4me.zip` as an optional release asset.

Minimum Home Assistant version for bundled local brand assets: **2026.3.0**.

## Recipe Hub panel

A **Cook4Me** sidebar panel is registered automatically and provides:

- **Official recipes** — search the SEB/KRUPS catalog, inspect ingredients and steps, and send official recipes to the appliance.
- **For my fridge** — rank official recipes against the saved pantry/fridge list and show matched/missing ingredients.
- **My recipes** — create and store manual cook-along recipes in Home Assistant.
- **Pantry & diet** — save pantry items, omnivore/pescatarian/vegetarian/vegan mode, allergies, dislikes/avoid terms, and preferences.
- **Eating-habit ranking** — repeated ingredients/categories from successful official recipe sends become small ranking-only hints. They never override dietary/allergy safety rules.
- **AI recipe** — use an already configured Home Assistant Conversation agent to generate a recipe from the pantry/profile/request. AI output is revalidated deterministically before it can be saved.

Official search data is hydrated before card rendering so title/photo/ingredients/steps can be normalized before grouping and display.

## Standalone-proven official search

The active Recipe Hub search uses the current KRUPS endpoint:

`POST /common-api/v4/search/recipes`

The request body was not guessed inside Home Assistant. It was isolated and verified in a standalone process with **no Home Assistant, no MQTT and no login token**.

For the German Cookeo proof (`q=risotto`, `de`, `GS_DE`) the working request body is exactly:

```json
{
  "fieldFilters": [
    {"field": "lang.key", "values": ["de"]},
    {"field": "market.key", "values": ["GS_DE"]},
    {"field": "applianceGroups.reference.key", "values": ["APPLIANCE_GROUP_15"]},
    {"field": "topRecipe.type.key", "values": ["BRAND"]}
  ]
}
```

with the normal v4 query parameters (`lang`, `market`, `page`, `size`, `q`, `groupBy`, `myUniverse`, `myOwnRecipe`, `withAutomaticSpellcheck`).

The proof returned **29 German KRUPS Cookeo serving variants** and hydration collapsed them by the real SEB `groupingId` into **exactly 11 logical recipes**, matching the KRUPS app result count. The proof set includes `Pfifferling-Risotto`, `Risotto "Aus Vorräten"` and `Risotto mit roten Linsen`.

The older speculative request body containing `fieldList`, `classifications.key_FOOD_COOKING`, privacy/source filters and empty filter lists is deliberately no longer used. Those fields were tested independently outside HA: some were unnecessary, some reduced the result to zero, and the old full field list could produce `INVALID_INPUT`.

## One logical recipe: languages → servings

Recipe Hub models one logical recipe as:

- **language variants** for that recipe; and
- **serving variants** inside each language.

Recipes sharing the proven SEB `groupingId` are shown as one card even when several siblings are returned. The card/detail exposes a recipe-language selector containing only languages actually discovered for that logical recipe.

Within the selected language, 2/4/6-person publications appear in a servings selector instead of separate cards. For same-language publications where SEB used different top IDs, the integration also collapses only the conservative exact-match case: identical normalized title **and** identical recipe-cover URL.

Changing either selector reloads the corresponding official detail so title, ingredients and steps match the chosen source language and serving amount.

Appliance delivery remains separate from display selection. A displayed serving is sendable only when an exact same-serving device-locale official variant is available; the integration never invents or scales a send variant.

## Recipe language controls

Recipe Hub has a global **Recipe language** selector:

- **Automatic (Home Assistant language)** — use the current HA UI language for the display catalog.
- A specific SEB/KRUPS catalog language — request/filter that source language.

The language list is limited to language/market combinations observed in SEB/KRUPS recipe content. This includes Greek, German, English, French, Italian, Spanish, Portuguese, Slovak, Hungarian, Czech, Bulgarian, Polish, Romanian, Turkish, Ukrainian, Russian, Japanese, Korean, Chinese and others.

In addition to the global source-language filter, each logical recipe can expose its own language selector when multiple siblings were actually found.

### Persistent Recipe Hub preferences

Recipe Hub controls are stored through Home Assistant `Store` per Cook4Me config entry. The integration remembers:

- global recipe-language selection;
- translate-results toggle;
- last Recipe Hub tab;
- live search draft;
- per-recipe selected source language; and
- per-recipe selected serving amount.

These settings survive panel reloads and Home Assistant restarts.

### Optional translation with the default Home Assistant AI Task

Recipe translation is **not** tied to an arbitrary Conversation agent.

The panel enables **Translate results to Home Assistant language** only when Home Assistant has a usable preferred/default AI Task for data generation (`gen_data_entity_id`). Translation follows Home Assistant's native `ai_task.generate_data` preference behavior.

- If a default AI Task exists, foreign-language result text can be translated to the HA UI language.
- Search results are hydrated first, including full step instructions, and only then translated; cards and Steps therefore stay in sync.
- If no default AI Task exists, nothing is treated as an error: the original SEB/KRUPS text is left as-is.
- If the AI Task provider fails, search/detail still succeeds and the untranslated recipe remains visible.
- Translation is display-only. `groupingFunctionalId`, recipe IDs, serving/send variants and Cook4Me commands are never changed by AI.

## Persistent Recipe Hub cache

Normalized catalog data is cached through Home Assistant `Store` per Cook4Me config entry:

- **search cache** — keyed by search context/query/locale and automatically invalidated when it predates the standalone-proven Cookeo/BRAND contract;
- **detail cache** — keyed by display locale and variant ID;
- **translation cache** — keyed by a hash of the source recipe text plus target language.

Repeated searches and translations survive panel reloads and Home Assistant restarts instead of repeatedly calling SEB or the AI Task provider.

Caches are bounded and time-limited. Search entries currently live up to 7 days, detail entries up to 30 days, and translations up to 90 days. Explicit refresh bypasses cached catalog results.

Recipe photo URLs are retained as part of normalized recipe data; normal browser/HTTP caching remains responsible for the image bytes themselves.

## Official recipe delivery

The integration resolves exact official SEB IDs from recipe detail before sending:

- shadow `recipe.functionalId` = `groupingId.functionalId`
- shadow `recipe.variant.functionalId` = recipe `fid.functionalId`

Sending is blocked when:

- the Cook4Me is offline;
- another recipe/session is still loaded on the appliance; or
- the recipe violates the saved diet/allergy/avoid profile.

This matches the live evidence from the Wi-Fi Cook4Me: when a recipe is already loaded, AWS accepts/consumes a new desired recipe but the appliance does not switch to it.

## Manual and AI recipes

Manual and AI recipes are stored as **Home Assistant cook-along recipes**. They are deliberately not sent to this Wi-Fi Cook4Me because no proven SEB custom-recipe upload ID/endpoint exists for arbitrary user-generated recipes.

## Entity cleanup / compatibility

The current release adds one default **State** summary sensor containing the useful live state as attributes:

- connected/updating/status/phase
- current recipe and exact IDs
- ingredients/exclusions/yield/durations
- step/instructions/next instruction
- program and timers
- firmware and connection timestamps
- `can_accept_recipe` / loaded recipe information

The existing granular sensors are retained for compatibility but are disabled by default for new entity registrations. Existing enabled entities remain untouched by Home Assistant's entity registry, so old automations are not silently broken. `Connected` remains a dedicated connectivity binary sensor; `Updating` remains available but is disabled by default.

## Services

- `cook4me.send_recipe`
- `cook4me.search_recipes` (response-only)
- `cook4me.recommend_recipes` (response-only)

For `send_recipe`, the recommended input is only `variant_id`; the integration fetches official detail and resolves/validates the exact IDs itself.

## Storage

Per-config-entry Recipe Hub profile/user data, UI preferences and the persistent recipe cache are stored through Home Assistant `Store` under `.storage`.

## Upgrade

Update HA-Cook4me from HACS and restart Home Assistant. The config-flow version is unchanged because no config-entry schema migration is required.

After restart, open **Cook4Me** from the Home Assistant sidebar. The panel module URL is versioned so the v12 update is cache-busted.

## License

MIT License. See `LICENSE`.

## ❤️ Voluntary support

This is a private hobby project maintained in my free time and provided independently of contributions.

If you enjoy the project and would like to send me a voluntary personal thank-you, you can use **[Ko-fi](https://ko-fi.com/chreece)**.

Contributions are completely optional and do **not** buy or guarantee features, support, development work, early access, priority, or any other service. This is not a charitable donation and no donation receipt is issued.
