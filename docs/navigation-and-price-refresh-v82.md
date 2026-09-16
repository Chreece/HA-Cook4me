# Icon navigation, recipe creators and price refresh (v82)

The main navigation is, from left to right: Today, Week, Search recipe, Cooking
book, Recipe creator, Shopping list, My kitchen & preferences. Buttons contain
only icons, with translated accessible labels, hover titles, focus outlines and
selected-state indicators. The seven buttons fit a 360 px viewport. The deferred
legacy icon decorator is overridden so it cannot put the old text labels back.

Recipe creator combines manual and AI creation in independent expandable sections.
The saved recipe list remains below them. Manual quantities, units, title, steps
and notes survive ingredient edits and re-rendering; AI inputs survive navigation
and resource loads. A saved old AI-tab preference opens the combined creator with
its AI section expanded. Creation results are scoped to the initiating account and
device; late AI responses cannot expose a previous user's recipe.

## Why prices were missing

The earlier exact-name mapping had only 32 food categories and 48 names. It now has
58 categories and 97 explicit names, including different forms such as dried versus
canned pulses, rice varieties, dairy, oils and vegetables. Category identifiers were
checked against the official Open Food Facts taxonomy on 2026-09-16. Three existing
invalid tags were corrected: tofu uses `en:plain-tofu`, courgette/zucchini uses
`en:zucchini`, and garlic uses `en:garlics`. Prepared foods and compound ingredient
names are still not collapsed into a raw food using fuzzy matching.

The product-price endpoint also compared local catalog rows by name while the UI
sent their `id`/`ingredientId` as a key. Those valid selections were rejected. The
endpoint now accepts the catalog's explicit IDs while still requiring a real
catalog match. Recipe inputs containing `id` are normalized as well. No provider
identity or nutrient identity is assigned to a different ingredient.

A newer observation and an older category estimate on the same date could tie and
leave the old price selected. Update time now breaks the tie, after purchase/manual
priority and observation date. The derived-cost cache version is bumped. A fresh
confirmed ingredient/barcode observation is reused without a redundant second
lookup. Source failures remain visible even when saved prices cover the recipe.

Coverage is still bounded by real evidence: same country and currency, an explicit
package/kg/item basis, a convertible recipe quantity, and observations no older
than 180 days. No grams-per-item or volume-to-mass conversion is invented. Each
unpriced ingredient now explains whether its quantity is missing, its food category
is unmapped, its units are incompatible, no local observation was found, or the
lookup budget/source failed. Entered purchase prices remain higher priority.

## Update timing and manual refresh

There is no scheduled background price refresh. Opening/expanding a recipe requests
costs. Successful saved observations are reused for 24 hours; lookup responses and
misses for 1 hour; source errors for 1 minute. The frontend also coalesces repeated
cost requests for 1 minute. The settings screen explains this policy.

The top toolbar's **Update recipe prices** icon refreshes the recipes rendered in
the current section, including collapsed cards, and places cost badges on them.
It does not traverse unloaded search results or other sections. Recipe fullscreen
has the same action, scoped to the open recipe. Missing recipe details are loaded
before costing; identical payloads are deduplicated. Navigation/account/device
changes invalidate the operation and late automatic results cannot overwrite a
manual refresh.

The read-only `cook4me/v34/recipe_cost_refresh` endpoint accepts at most 32 recipes
per batch, authenticates device access, bypasses observation/miss and derived-cost
caches, and coalesces shared ingredient queries within the batch. It also works
when automatic lookup is disabled, without changing that preference. Existing
purchase evidence is preserved. Queries remain bounded to 3 concurrent external
requests, 15 seconds per query and a 30-second lookup budget per recipe; an
incomplete refresh keeps known values and says that prices are still missing.

Open Prices currently provides no country filter for its prices endpoint, so the
integration checks returned shop locations and currencies. It examines the latest
100 matching observations per query. A missing result does not mean an ingredient
has no price anywhere in the country.

Primary sources checked:
- https://prices.openfoodfacts.org/api/schema
- https://openfoodfacts.github.io/open-prices/
- https://static.openfoodfacts.org/data/taxonomies/categories.json

Active panel: v82; cache path: `2026.9.16.7`. No live HA/appliance deployment or
household price observations were available in this workspace.

## Validation

- All 1,447 Python tests passed on the runtime changes, including seven new
  tests for refresh caches, coalescing, authorization, catalog IDs, price priority
  and missing-price reasons.
- Real Chromium checked all seven icon buttons, restored AI navigation, independent
  creators, manual and AI saving, draft retention, English/German/Greek mobile
  widths, page versus fullscreen refresh scope, source failures/retry, late
  automatic responses and account isolation.
- The existing unified scanner/ingredient-click and automatic-price browser suites
  passed on v82. Desktop/mobile layouts were inspected. HA icon elements and API
  responses in the standalone harness are test fixtures.
- The generated bundle, JavaScript syntax, version contract and diff checks passed.
- Four additional pinned-installer tests passed, including failed activation
  rollback, wrong mounts and missing source files. This gives 1,451 passing Python
  tests across the runtime suite and v82 installer checks.

Runtime commit: `9b0aa5fce6734f71a9304cd72d64e9e0f3ae94be`.
The installer is `tools/deploy_offline_runtime_v82.sh`; it pins this runtime,
keeps the previous component, verifies the new panel and restores the backup if
activation fails. Reopen/reload Cook4Me after installation.
