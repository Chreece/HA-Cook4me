# Changelog

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
