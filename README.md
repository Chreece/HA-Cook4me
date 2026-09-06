# HA-Cook4me — Recipe Hub

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
![Version](https://img.shields.io/badge/version-2026.9.6.6-blue.svg)

**Current version:** `2026.9.6.6` · version format: `YYYY.M.D.BUILD`

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

- **Official recipes** — search the SEB/Cook4Me catalog, inspect ingredients and steps, and send official recipes to the appliance.
- **For my fridge** — rank official recipes against the saved pantry/fridge list and show matched/missing ingredients.
- **My recipes** — create and store manual cook-along recipes in Home Assistant.
- **Pantry & diet** — save pantry items, omnivore/pescatarian/vegetarian/vegan mode, allergies, dislikes/avoid terms, and preferences.
- **Eating-habit ranking** — repeated ingredients/categories from successful official recipe sends become small ranking-only hints. They never override dietary/allergy safety rules.
- **AI recipe** — use an already configured Home Assistant Conversation agent to generate a recipe from the pantry/profile/request. AI output is revalidated deterministically before it can be saved.

Official search results are grouped by the SEB recipe `groupingId`, so serving/language variants do not appear as duplicate cards. Recipe photos are selected only from recipe-level media, and step text comes from the real SEB mobile recipe fields.

### Recipe language controls

Recipe Hub has a **Recipe language** selector:

- **Automatic (Home Assistant language)** — use the current HA UI language for the display catalog.
- A specific SEB/KRUPS catalog language — strictly filter results to that language instead of silently falling back to a different one.

The language list is limited to language/market combinations observed in the SEB/KRUPS recipe content used by the integration. This includes Greek, German, English, French, Italian, Spanish, Portuguese, Slovak, Hungarian, Czech, Bulgarian, Polish, Romanian, Turkish, Ukrainian, Russian, Japanese, Korean, Chinese and others.

Recipe display language and appliance delivery remain separate. A displayed/localized sibling can be shown while the Cook4Me/device-compatible official variant is retained independently for sending.

When no exact sibling exists in the selected/HA language, Recipe Hub falls back to the configured Cook4Me/device-locale recipe rather than an arbitrary foreign sibling returned by the target market. If that fallback arrived as an ID-only search row, the panel fetches its official detail on demand so the user still sees the real source-language title, photo, ingredients and instructions rather than a numeric recipe ID.

### Optional translation with the default Home Assistant AI Task

Recipe translation is **not** tied to an arbitrary Conversation agent.

The panel enables **Translate results to Home Assistant language** only when Home Assistant has a usable preferred/default AI Task for data generation (`gen_data_entity_id`). Translation follows Home Assistant's native `ai_task.generate_data` preference behavior.

- If a default AI Task exists, foreign-language result text can be translated to the HA UI language.
- If no default AI Task exists, nothing is treated as an error: the original SEB/KRUPS text is left exactly as-is.
- If the AI Task provider fails, search/detail still succeeds and the untranslated recipe remains visible.
- Translation is display-only. `groupingFunctionalId`, recipe IDs, send variants and Cook4Me commands are never changed by AI.

A manually selected recipe language can therefore be used either as a strict original-language filter, or together with the translation toggle when a default AI Task is configured.

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

Per-config-entry Recipe Hub data is stored through Home Assistant `Store` under `.storage` and includes only the pantry/profile, manual/AI recipes, and limited recipe-send history used for ranking.

## Upgrade

Update HA-Cook4me from HACS and restart Home Assistant. The config-flow version is unchanged because no config-entry schema migration is required.

After restart, open **Cook4Me** from the Home Assistant sidebar. The Recipe Hub panel module is versioned so this release does not reuse an older cached JavaScript panel.

## License

MIT License. See `LICENSE`.
