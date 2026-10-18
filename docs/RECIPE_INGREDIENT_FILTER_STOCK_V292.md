# Ingredients and household-stock recipe filters

The **Ingredients** recipe filter is the single place to select manual preferred
ingredients, seasonal ingredients and saved-stock constraints. The standalone
**Only what I have at home** toolbar button is no longer displayed. This is a
navigation change, not a new recipe-query contract: the same per-view
`onlyHome`, `preferExpiring`, `maxMissing`, `avoidRecentDays`,
`seasonalIngredients` and `ingredients` preferences are saved unchanged.

## Using the dialog

Open Ingredients to see the four at-home options, seasonality, and a collapsed
**Choose preferred ingredients** section. The section summary reports the number
of selected ingredient checkboxes. Expand it to search the catalog, select or
clear visible items and inspect saved selections. The same original checkbox
nodes and input/change handlers stay attached, and the section is collapsed
each time the filter is opened. Apply saves everything in one request.

The Ingredients toolbar icon reports relevant active at-home options and manual
ingredient selections. The seasonal leaf indicator remains separate visual
evidence on the same Ingredients icon. Filter settings stay scoped to the
current recipe view and Home Assistant user/integration entry.

## Physical-stock and recipe coverage consistency

An existing stock identity mismatch was found: `stock_for_ingredient()` accepts
reviewed `identities` and explicit row-level `ingredientLinks`, but
`stock_allocation.allocate_stock()` formerly connected physical lots only by
the row primary identity and individual lot links. For a Japanese/Korean recipe
ingredient whose stored package was linked at the row level, the same package
could be discoverable for storage places but contribute *zero* usable stock.

The allocation graph now uses the **primary stored ingredient identity**
plus explicitly saved row-level and lot-level `ingredientLinks` for each
physical lot. Finite package normalization also preserves and merges those
explicit assignments. Broad calculated catalog aliases are deliberately
**not** allowed to grant additional physical-lot capacity: otherwise an
unconfirmed food could borrow a different product's stock. Reviewed aliases
remain available for read-only lookup, but only explicit source assignments
or the stored primary ID establish allocation edges.

A physical package contributes capacity only once across multiple recipe
requirements. No inventory is changed by a read, translated display names
never establish matches, and unsupported conversions remain unknown.

Stored recipes may also contain old match/quantity annotations. When a live
stock package has a positive quantity (or is unlimited) and is provably linked
to the recipe ingredient using the same reviewed frontend identity test used
for its storage location, a stale zero/missing annotation is not shown as an
authoritative 0%. Instead, the ingredient explicitly shows **At home /
Στο σπίτι** with a tooltip that the amount needs verification. The overall
card percentage is marked unknown while that inconsistency remains. This
does not assert that enough of the ingredient is available, and never changes
the recipe, physical stock, dietary restrictions or backend match metadata.

Fresh calculations use the corrected server allocation and continue to report
exact shortages, reviewed portion conversions, and unknown incompatible units.

## Tests

- Backend Japanese/Korean row-link and source-alias allocation, shared-lot
  no-double-spending, unrelated-ID nonmatches, incompatible units and
  read-only stock preservation.
- Frontend unit checks for collapsed filter settings, correct active badge
  counts and evidence-only stock-presence reconciliation.
- Full frontend Chromium at 390px and 1440px with Greek labels, persistent
  Home fields, retained seasonal/search/bulk handlers, collapsed list, Korean
  rice with a Greek storage-place name, and same-name/unrelated-ID guards.
- Existing runtime stock, seasonal filter, daily/weekly generation, recipe
  detail and HACS packaging suites remain active.

There is no migration of stored user data or recipe cache required. The active
frontend custom element and query string are versioned to avoid continuing
to use an already registered panel constructor after installation.
