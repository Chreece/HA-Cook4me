# Offline ingredients and price coverage (v84)

The full offline ingredient catalog is available in a dedicated searchable browser
in My kitchen & preferences. The same loader serves product assignment, diet
exclusions, recipe filters and the recipe creator. Ingredient details remain
offline; adding a product opens the existing fullscreen scanner/manual form with
the ingredient selected. The old advanced stock-entry form stays removed.

The bundled catalog was intact. The previous loader returned immediately to a
second caller while the first request was running, so concurrent consumers could
see an empty list. Failed requests could leave a blank picker with no retry; the
expanded diet picker also forced repeated requests on failure. v84 shares one
promise per account/device/language, provides retry, and rejects stale responses
without blocking a newer account or language request. Stored stock is expanded
by default. No stored ingredients or household preferences are rewritten.

## Price coverage

The exact-name mapping grows from 97 names/58 categories to 259 names/202 categories.
All identifiers were checked against the official Open Food Facts category taxonomy
on 2026-09-16. In the shipped catalog, mapped ingredient occurrences increase from
71,116/230,486 (30.9%) to 137,135/230,486 (59.5%). This measures eligibility for a
category lookup, **not the proportion with an actual observed price**. Frequent
previously unmapped foods include butter, white potatoes, ginger, herbs, chicken,
fish, additional cheeses and baking ingredients. Ambiguous mixtures, water and
unspecified pepper are not assigned a guessed category.

Lookups try both loose and packaged observations when the preferred type has no
compatible result. They inspect up to five pages of 100 observations within a
15-second total request budget, with at most three external requests running at
once. Every observation still requires the requested country/currency and an
explicit compatible quantity basis. The provider's current price endpoint has no
country filter. Search limits, missing quantities and incompatible measurements
remain visible rather than becoming zero cost.

Cook4Me unit identifiers normalize localized mass, volume and item labels for
costing. Fresh item-based and weight-based price references can coexist; an
incompatible fresh reference no longer prevents another usable lookup. Unknown
amounts and unsupported measurements do not consume external lookup slots. No
spoon volume, density or grams-per-item estimate is invented. Original recipe
quantities, program and device payloads are unchanged.

Slow price queries previously outlived the recipe's 30-second wait but lost the
ingredient hydration that saved their results. v84 returns a partial cost after
20 seconds while shared background jobs finish saving the evidence. Visible
recipes poll those existing jobs without forcing new provider lookups; polling
stops on navigation/context change, disconnection or after three minutes.
Finished results persist even if the user closes the recipe. Pending work has a
separate status from provider failure. Job admission is capped at 500 and the
existing per-recipe limit remains 24. Price refreshes are still on demand.

Live read-only checks for Germany/EUR found usable carrot (loose and packaged),
ginger and butter observations; individual requests took approximately 10–14
seconds in this environment. These checks demonstrate provider behavior, not
coverage of the user's configured market. No live HA instance or appliance was
available for deployment verification.

Primary provider sources:
- https://prices.openfoodfacts.org/api/schema
- https://github.com/openfoodfacts/open-prices/blob/main/open_prices/api/prices/filters.py
- https://static.openfoodfacts.org/data/taxonomies/categories.json

## Validation

Real Chromium loads actual bundled catalog rows from an empty cache, including
English and Greek, and checks browsing, scanner assignment, exclusions, recipe
filters, creator availability, failure/retry, concurrent callers, late language
responses and mobile overflow. The existing profile, navigation, price-refresh,
scanner and pricing browser suites pass on v84; price-refresh coverage includes
pending results updating automatically. The real WebSocket scheduler returns
English, Greek and German offline catalogs without contacting the recipe cloud.

Backend regressions cover pagination beyond foreign/wrong-unit pages, bounds,
partial failures, loose/packaged fallback, localized units, compatible references,
lookup budgets, and hydration continuing after a partial response. Purchase and
manual prices retain priority and mixed currencies are never combined.

Active panel v84, cache path `2026.9.16.9`, bundle namespace `build-2026091609`.

The full Python run exercised 1,477 tests; its only three failures were stale
active-panel assertions still expecting v83. Those assertions were updated to v84
and the affected suites passed together with the final pricing regressions.
Additional focused tests cover unknown measurement budgets and continued hydration.
Bundle generation, JavaScript/Python syntax, version and diff validation passed.
