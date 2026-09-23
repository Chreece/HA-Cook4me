> Consolidation note: the previously local patch documented below is included in v197. Original fixture-test and publication notes are retained as history; see BRANCH_CONSOLIDATION_V197.md for current validation and scope.

# Cook4Me price audit — v189 focused batch

Date: 22 September 2026.
Base: `Chreece/HA-Cook4me`, `175e285cae0f1f1e05ae2cdc3276134543cbf14d` (v188).
Status: local patch prepared; GitHub publishing was blocked. No branch, main, release or live Home Assistant installation was updated.

## Scope

This batch audits the price-only unit adapter, recipe and consumption costing, persistent recipe-price fingerprints, and concurrent cache initialization. It continues the Greek-language work through explicit price-unit normalization and current-language labels on cached cost rows. The v188 weekly UI → supermarket → original-language formatting remains unchanged.

The audit does not claim that current retailer prices or all bundled price observations have been independently verified. It does not change the ingredient catalog, overwrite paid purchase prices, alter cooking instructions, convert currencies, or assign guessed prices to unknown ingredients.

## Findings and corrections

| Finding | Consequence | Correction |
|---|---|---|
| Price unit normalization omitted explicit Greek metric, count and spoon labels. | A quantity could be visible in Greek but fail to match the price reference's measurement. | Normalize explicit `γρ.`, `γραμμάρια`, `κιλά`, `χιλιοστόλιτρα`, `λίτρα`, `τεμ.`, `κ.σ.`, `κ.γ.` and reviewed full-word variants in a price-only copy. Normalize final sigma and composed/decomposed accents on both sides. |
| The measurement helper rejected decimal-comma quantities accepted by the ordinary cost parser. | For example, `1,5 κ.σ.` lost its usable amount and disclosed spoon-volume estimate. | Normalize the numeric comma before measurement processing. Invalid, non-finite and negative quantities remain invalid. |
| Costing discarded explicit identities before stock allocation. | A reviewed alternate ingredient identity could match in stock coverage but disappear when identifying paid lots for pricing. | Preserve `identities` and explicit `identity` in the price request without mutating the source row. |
| Recipe-cache stock matching used fewer identities than allocation. | Changes to a matching stock lot, its barcode or its paid reference could leave an old recipe price cached. | Fingerprint the same explicit identities, linked lot identities, relevant paid references and barcode references. Unrelated stock remains excluded. |
| Fingerprints omitted global FEFO ordering metadata and some recipe evidence. | Changing opening/expiry dates across stock rows or changing quantity evidence could fail to refresh derived prices. | Include best-before, opened-at, use-within-days, added-at, alternate ingredient IDs, string ingredients and quantity provenance. Advance the calculator and preview evidence revisions. |
| Concurrent first access could create multiple cache objects for one entry. | Separate requests could calculate and save through separate in-memory caches. | Use the existing per-entry store initialization lock, while keeping calculation in the executor. |
| A cached cost row retained the first language's ingredient name. | Switching language could leave old names even though the numeric price remained valid. | Rebind current names on a one-to-one cache hit, without recalculating unchanged price evidence. |
| Exact-lot and consumption reference lookup omitted compatible-unit filtering in two paths. | An incompatible reference could hide an available compatible barcode observation. | Supply the measurement unit during reference selection; retain the exact paid currency and label barcode fallback as estimated. |
| Empty consumption reports could iterate over `None`; a zero package basis could be marked usable. | Cost history could raise an exception or retain an unusable observation. | Treat absent deducted lots as an empty report and require a strictly positive package basis. |

Explicit unknown labels such as a pinch, a bunch, a packet or an unspecified spoon are not converted into arbitrary grams or pieces. Stable provider unit identifiers retain precedence. These changes do not introduce fuzzy ingredient matching.

## Validation

`python tests/test_price_audit_v189.py`: **41 tests passed locally**.

The initial regression batch reproduced failures before implementation. The empty-report and zero-package-basis cases were separately reproduced before their fixes. Changed Python files compile.

Tests cover explicit Greek units, Unicode/case handling, decimal commas, source immutability, provider-ID precedence, unresolved ambiguous units, invalid quantities, existing German/French labels, proportional package costing, unknown versus explicit zero prices, mixed currencies, partial paid-stock plus estimated remainder, cache reuse, force refresh, persistent reload, deep-copy isolation, stale fingerprints, current display names and eight simultaneous cache initializations.

Synthetic arithmetic examples are not retailer quotations: a EUR 2.40 / 200 g reference gives EUR 0.30 for 25 g; 10 g from a EUR 2 / 100 g paid lot plus a remaining 15 g at EUR 4 / 100 g gives EUR 0.80 total, not a duplicated full-quantity estimate.

These are isolated unit tests. Storage, stock allocation, budget fallback and catalog I/O are controlled test doubles; production source functions are selected by AST. Local testing used fetched source excerpts for some unchanged dependencies. The bundled regression file uses the full repository's source when run there. Full repository CI, browser rendering, a live Home Assistant instance and current Open Prices observations were **not** executed or verified in this batch. The existing CI workflow is patched to include the new regression suite, but that workflow has not run on these changes.

## Apply and rollback

Use the bundled `apply_price_audit_v189.py` against a local Git checkout. It checks the exact original file hashes, refuses to overwrite unrelated edits or newer source, creates a persistent backup, applies only the six payload files and executes the focused tests. A failed validation restores the original files and removes newly created files. It neither commits nor pushes, restarts Home Assistant, nor installs into the live configuration.

The runtime manifest is unchanged. This is a development patch, not a published HACS release.

## Remaining verification

Run the repository's complete validation workflow against the applied working tree, inspect the actual persisted household price store for coverage and stale observations, and check the recipe/weekly/shopping views on the real installation. Those checks must be completed before claiming an exhaustive price or deployment audit.
