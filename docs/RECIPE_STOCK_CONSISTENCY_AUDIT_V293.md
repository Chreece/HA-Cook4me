# Recipe stock coverage: general consistency audit

## Scope

The availability of **every recipe ingredient** must follow the same evidence
contract, whether the recipe is Japanese, Korean, Greek, Polish, English or any
other published language. A pantry location label proves a linked product can
be located, but does not by itself prove that the recipe's required quantity
is available. A price indicator is separate from stock coverage and may remain
unknown (`—`) when a package has no reliable price.

The audit covers:

- finite packages with known, partial or depleted amounts;
- explicit unlimited staples (salt, pepper, water, sugar and other products);
- unknown recipe quantities and incompatible/nonreviewed source units;
- duplicated recipe ingredients sharing one physical package;
- catalog-backed foreign-language source identities and explicitly assigned
  pantry links;
- unrelated items sharing translated names or different food preparations;
- saved recipe matches that can be older than the current pantry;
- the ingredient chip inside fullscreen recipes and aggregate card badges.

## Root causes in the existing code

1. `food_intelligence.recipe_quantity_feasibility()` checked for a missing
   recipe requirement **before** checking `current.unlimited`. An explicit
   unlimited stock item with an unknown recipe quantity therefore became
   `unknown_requirement` and its badge displayed `—`.
2. The v292 ingredient badge repair synchronized uncertain finite-stock
   presence but did not update explicit unlimited stock. The later v79 recipe
   pricing/storage rendering layers could replace an already-known unlimited
   badge with the stale `—` placeholder.
3. The photo-level recipe badge used cached `match.quantityCoverage` even when
   the live pantry had a reviewed unlimited match. This could contradict the
   fullscreen ingredient badges.
4. The storage-location renderer listed places from every historical lot,
   including packages at **zero quantity**, and omitted a location from some
   legacy positive finite-stock rows that have no `lots` array.

## Correct behavior

- **Verified unlimited stock**: use `coverage=1.0`, `status=enough` and
  `unlimited=true` even when the official recipe omits a quantity. The
  fullscreen chip displays **∞** with a localized "unlimited stock" tooltip.
  The stored location remains visible.
- **Verified finite amounts**: display the calculated exact coverage
  percentage and never convert a proven shortage to full availability.
- **Present but amount unclear**: display **At home / Στο σπίτι** and retain
  the uncertainty in aggregate figures. Do not invent 100% stock.
- **Missing stock**: show the actual 0% shortage if calculated, or `—` for
  genuinely unresolved availability. A matching translated display name
  alone is never enough to match a product.
- **Unknown or incompatible measurement**: remain unknown unless a physically
  linked unlimited item makes the requirement automatically satisfiable.
- **Depleted physical lots**: cached row totals must not turn lots with
  zero quantity into a positive stock match; depleted-lot storage locations
  are not shown as places with usable food.
- **Legacy positive finite rows**: a stored location still appears when an
  explicit quantity is positive even if the older stock record has no lots.
- **Shared physical package**: the existing allocation graph spends one lot
  only once across all recipe lines.
- **Price unknown**: the per-ingredient *price* may independently remain `—`.
  Stock presence must not be inferred from price, or vice versa.

The backend change is one ordering correction. The frontend v293 layer is
additive, preserving the v292 home/ingredients filter UI and using a fresh
custom-element identity plus URL marker to prevent stale browser code. All
display reconciliation is read-only and never writes a recipe, a stock record
or a cloud device command.

## Automated audit coverage

`tests/test_general_stock_consistency_v293.py` exercises finite vs unlimited
stock, known vs unknown measurements, multilingual source IDs, exact package
links, missing products, diet-staple semantics, same translated names and
one-lot multi-recipe allocation, without Home Assistant or live household data.

`tests/test_stock_consistency_v293.mjs` checks the pure frontend reconciliation,
including all-unlimited and mixed/unknown aggregate calculations.

`tests/browser_stock_consistency_v293.py` loads the real current frontend in
Chromium at **390px mobile and 1440px desktop**, with synthetic Greek/German/
Japanese/Chinese ingredient names. It validates salt, pepper and water as ∞;
rice at two distinct source-index percentages; unrelated but same-named food
as 0; depleted packages as 0 despite still having a storage place; and
persisted ingredient/recipe objects remaining unmodified.

Existing ingredient identity, diet, scanner, stock, HACS and menu filter tests
continue to run. The browser fixture uses no private inventory or connected
cooker. If a live household still has unknown availability after installing
this version, examine the persisted explicit ingredient links and source ID
before adding any new alias. Do not guess by translated names.
