# Runtime delivery, weekly cleanup and stock coverage — v198

Base: `fde5b1d676de665bad65c379f40753812794b7c9` after the v197 consolidation.
This patch does not change saved inventory, nutrient evidence, price observations,
tags, releases or the user's Home Assistant configuration.

## Findings and fixes

1. Weekly Leftovers/remainings and Ingredient prices had already been wrapped by
   the v137 layout. The v195 cleanup only inspected v179 folding keys, leaving
   those older wrappers visible. Remove the two exact v137 panels as well as the
   four existing v179 keys. Shopping requirements, meal slots, nutrition and totals
   remain. Data is not deleted.
2. The v196 editor exists in main, but its merge retained the panel load URL. Use
   a new `/runtime-v198` static path and a new registered panel constructor. All
   relative modules receive the new URL prefix, including the unchanged v196
   editor. The existing outside lower-right Save/Discard controls and barcode
   search are retained, not duplicated. New manual forms and field/confirmation
   focus use the same tested editor behavior.
3. Recipe quantity calculations discarded `ingredientId`/`id` when looking for
   stock, while scanner choices saved a stable key with a localized name. Resolve
   those explicit IDs before allocation. Prepare trusted canonical-name,
   reviewed preparation-alias and food-concept membership once in HA's executor.
   This also joins reviewed locale/provider IDs such as the Skyr source records.
   Arbitrary translated-label equality, fuzzy names, display groups and unknown
   product forms are not evidence that two keyed foods are interchangeable.
4. Normalize explicit provider unit IDs and reviewed localized units on calculation
   copies, not stored records. Existing ingredient-specific portion conversions
   and shared-lot allocation remain authoritative. For example, one garlic clove
   can use its existing reviewed gram conversion without counting a whole bulb.
5. The browser previously converted null coverage with `Number(null)`, yielding
   a misleading 0%. Unknown quantity or incompatible-unit coverage now stays
   unknown. A measured true shortage is still 0%. Original ingredient-row indices
   distinguish repeated lines that consume different shares of one physical lot.

The manifest remains `2026.9.22.7`; `v198` is an explicit frontend/runtime revision,
not a new tagged release. The active element ends in `-runtime-v198`, and the UI
adds `data-cook4me-ui-revision="198"`. Install updated main and restart HA before
opening/reloading the panel. There is no automatic live deployment in this PR.

## Update/startup timing

A direct download/copy/restart operation and an ordinary in-panel update are
separate timings. We have not timed the user's server. Local cold catalog
preparation took about 13–19 seconds in the test environment; this is not a
measurement of their whole HA restart or a promise of a particular startup time.
The integration now logs `Cook4Me catalog and stock index ready in X.XX seconds`
at info level. It records only elapsed time, never inventory or user data. The
catalog and identity index are prepared off the event loop. This change fixes
correctness/delivery; it does not claim to eliminate the user's reported minute.

HA guidance on avoiding blocking I/O/CPU in the event loop:
https://developers.home-assistant.io/docs/asyncio_blocking_operations/

## Validation

- 28 new production-backend tests: IDs, source precedence, localized units,
  portion conversion, shared capacities, distinct food forms, unknown coverage,
  optional/unlimited stock and no persistent mutation/per-request disk I/O.
- 3 shipped-catalog tests, including 7,434 Greek/German picker-choice checks on
  the local catalog (3,365 Greek and 4,069 German), reviewed Skyr siblings and
  the Greek garlic-clove case. No real user stock is used.
- 21 JavaScript tests for coverage identity, unknown-vs-zero, repeated ingredients
  and both weekly folding generations.
- 99 retained editor/receipt/suggestion JavaScript tests passed alongside those
  21 new tests. The legacy receipt selector test now asserts the exact six
  allowed selectors, rather than the old count of four.
- 12 retained universal/reviewed-portion backend tests passed.
- Existing source-validation command group passed locally.
- Chromium checks at 390x844 and 1366x900 loaded the complete v126→v180 inheritance
  chain plus the new runtime constructor. Visible Save/Discard/lookup, first
  invalid field, barcode suggestions, clean successful saves, X→Keep editing
  focus and discard were checked with controlled HA/API/module loading. No
  JavaScript page errors occurred. These are not real camera or live-HA tests.

Local recovery used the pre-consolidation checkout plus the already-approved
v190 unit normalization; new changes were restricted to remote-verified base
files. The read-only PR workflows rerun against the full current v197 catalog
and source. Their conclusions, not the local fixture, determine merge readiness.
