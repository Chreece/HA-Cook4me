# Exclude ingredient cooking guides from automatic meals — v206

## Behaviour

Plain ingredient-cooking guides such as Rice/Reis/Riz, Carrots/Karotten,
Cauliflower/Blumenkohl and Bulgur/Boulgour must not be recommended as meals.
The exclusion applies to every automatic meal category, daily category rotation,
catalog-language balancing, weekly generation/regeneration and replacement,
and the older recommendation/voice ranking paths. It is a hard eligibility
filter, not a ranking penalty. Weekly taxonomy/variety fallbacks cannot bring
an excluded guide back merely to fill a slot.

Catalog search, recipe details, sending an explicitly selected recipe and manual
recipe creation remain available. Previously saved plans, cooked leftovers,
recipes and stock are not deleted or rewritten. Generate new Daily suggestions
or regenerate the desired Weekly meals to replace previously saved suggestions.
An explicit recipe-creation request still uses its dietary validation but is
not misreported as a dietary failure just because it requests a cooking guide.

## Evidence, not ingredient count alone

`recipe_suitability.py` is a shared, pure-data classification/selection helper.
It recognizes explicit guide-type metadata or one substantive food plus basic
food-title/preset-yield evidence. Water and narrowly named cooking aids do not
turn a guide into a complete dish. Repeated references to the same food do not
artificially increase the count. Whole canonical names take precedence over
translated labels, and measured source names such as `200 milliliters of water`
are supported without treating coconut water as water.

The compact release also contains weight/piece/cup-based ingredient presets:
zero preparation, a positive cooking duration, and an output matching the sole
food's quantity/unit instead of a diner count. This supports the same guide in
different languages and serving editions, even with imperfect source titles.
Opaque recipe-type IDs are never assigned guessed meanings.

This is not a minimum-ingredient rule or a substring blacklist. Rice pudding,
porridge, cauliflower soup, apple compote, banana ice cream, dulce de leche and
yogurt can remain eligible when they represent dishes rather than basic cooking
instructions. Milk, onions, garlic, stock and sauces are not discarded as cooking
aids. Sparse/malformed metadata alone is not proof of a guide; the existing
recipe validation and dietary-safety rules continue independently.

## Integration boundaries

- `websocket_v13._rank_filtered` excludes guides before costly annotation and
  truncation; its existing recommendation consumers inherit the rule.
- `shared_recipe_runtime.search_filtered` enables the same rule for automatic
  Daily/Weekly catalog searches before their ranking/candidate caps. The shared
  `processor` defaults to manual/search mode, retaining guides for Discover and
  saved-plan presentation while still applying all dietary filters.
- `recipe_hub.rank` covers legacy service/voice recommendation paths; `annotate`
  is unchanged, so manually chosen recipes remain accessible.
- Both daily selectors and the weekly candidate fallback add final safeguards.
  Daily category counts and empty categories describe eligible candidates only.
- `websocket_v22` explicitly keeps manual AI recipe validation outside this
  automatic-meal rule. Its allergy/diet validation remains mandatory.

No network or AI calls, catalog loads, inventory mutations or changes to ingredient
identity, cooking instructions, nutrition, costs, dietary restrictions or cooker
transport are introduced by the helper. It uses a bounded normalized-string cache.
The existing executor/progress/cancellation paths and slim HACS archive remain.

This is a backend-only change: no frontend file, runtime URL or manifest version
is changed. Install current main and restart HA before generating new suggestions.
There is no live deployment in this change.

## Validation

35 new tests pass locally: 31 classification/selector/ranking/catalog tests and
4 tests of the actual weekly generator/shared processor using the retained v200
controlled HA/scoring fixtures. Also passed: 15 retained progress/cancellation
and 5 retained weekly responsiveness/variety tests. The new import test failed
before the implementation existed. Catalog testing caught a measured-water label
that initially let one translated Pepper preset through; that regression is fixed.

The local catalog audit classified 7,388 basic-guide variants in 17 source
languages and checked all Rice/Carrots/Cauliflower/Bulgur/Bulgur wheat/Pepper
examples while retaining the audited simple desserts/yogurt. This local catalog
is the retained pre-consolidation snapshot, not a claim about live HA contents.
The dedicated read-only workflow repeats the audit on the full current repository.

The seven existing changed production files were reconstructed/read and verified
byte-for-byte against current main's Git blob hashes before editing. Publication
uses only this explicit delta over main `c8565a3652e849f5db018ba6cb876e6b50e2cd9e`;
it does not publish the old bootstrap checkout or its catalog. All existing CI
workflows remain enabled. No live user inventory, camera, AI or cooker was used.

```sh
python tests/test_meal_suitability_v206.py
python tests/test_meal_selection_routes_v206.py
python tests/test_week_progress_v200.py
python tests/test_weekly_responsive_variety_v181.py
```
