# Recipe cost coverage v86

The v85 catalog expansion barely improved practical recipe costing: most recipe
amounts still could not use its prices. v86 prices more real ingredient amounts,
loads offline previews on visible recipe cards, and explains incomplete totals.

## Measured result

DE/EUR, empty household inventory, bundled prices only; 32,163 language/serving
variants with 230,486 ingredient occurrences. These are not unique recipe families
and this is not a measurement of a user's live Home Assistant installation.

| Offline measure | v85 | v86 |
| --- | ---: | ---: |
| Priced ingredient amounts, all variants | 51,068 | 78,396 |
| Variants with no cost | 8,439 | 6,465 |
| Partial variants | 22,943 | 25,236 |
| Complete variants | 781 | 462 |
| Priced amounts, German-language variants | 4,117 | 6,473 |
| German-language variants with no cost | 528 | 430 |
| German-language partial variants | 1,813 | 1,944 |
| German-language complete variants | 73 | 40 |

German ingredient coverage rises 57.2%; 98 fewer German variants have no cost.
Complete counts fall because v85 included unsafe prepared-food and package matches.
More partial recipes also result when a previously unpriced recipe gains a subtotal.
We do not hide unpriced ingredients or call an incomplete subtotal a complete price.
The remaining gaps include missing amounts, unsupported measures, ambiguous food
names, water and ingredients without sufficiently recent local price evidence.

Reproduce with `python tools/audit_recipe_price_coverage_v86.py`. The companion JSON
contains all language counts and the largest remaining gaps. Household purchases
and live lookups may improve coverage beyond this offline baseline.

## Changes

- Visible cards request local cost previews automatically, with three requests at a
  time and entry-context isolation. Previewing does not contact price providers or
  rewrite the household price store. Opening a recipe still checks online.
- Offline lookup bypasses the network semaphore. The recipe endpoint returns saved
  and available estimates after two seconds while missing lookups continue.
- 52 reviewed USDA portion records cover 80 exact ingredient names. Teaspoons,
  tablespoons, cloves and selected whole-ingredient counts can use mass/volume
  price evidence. Explicit count identifiers UNIT_138 and UNIT_50 are understood.
- Native quantities and exact paid stock lots take priority. Cost-only alternatives
  preserve original cooking, stock deduction and nutrition data. Unlabelled counts
  require a reviewed whole-food name and at most 20 items; every assumption is shown.
- Source details show the estimated quantity and its source. Missing quantities and
  prices are named beside the subtotal. Cups, pinches, bunches, packs and entirely
  unspecified quantities remain unknown unless native price evidence matches.
- Rebuilt public observations reject known incompatible food forms, misclassified
  products, contradictory pack labels and ambiguous per-package counts. A stated
  500 g package is no longer one ingredient. The snapshot contains 371 observations,
  including 180 German observations, plus six separately attributed retail fallbacks.
- Existing external observations are rebuilt once under the new rules. Manual prices,
  purchase references, exact paid lots, settings and household stock are retained.
  Recipe cost fingerprints include quantity-evidence revision 86.

## Evidence and limits

Open Prices evidence retains its ODbL attribution and input hashes in
`catalog/observed_prices.v1.json`. Every observation stays country/currency scoped,
positive, dated and limited to 180 days. Discounts are not used.

[USDA SR Legacy](https://fdc.nal.usda.gov/download-datasets/) supplies the public-domain
portion records. `catalog/price_portions.v1.json` retains food IDs, portion IDs,
original gram amounts and descriptors. Four cup records are explicitly divided
into 16 tablespoons; this is an approximate cooking conversion. Spoon volumes use
[NIST's approximate cooking equivalents](https://www.nist.gov/pml/owm/metric-si/metric-kitchen/metric-kitchen-cooking-measurement-equivalencies):
5 ml per teaspoon and 15 ml per tablespoon. Portion size, packing and spoon conventions
vary, including 20 ml Australian tablespoons; the UI therefore labels these as
estimates, not measured recipe quantities.

Six German package prices were checked directly on dm listings on 2026-09-16:
whole cane sugar, baking powder, dry yeast, corn starch, vanilla sugar and ground
vanilla. Each row in `catalog/retail_prices.v1.json` links to its product page.
They fill compatible gaps only; Open Prices matches and user prices take precedence.
The named product variety is a generic ingredient estimate, not a national average
or an assertion of the user's actual purchase price. Whole cane sugar is disclosed
as the reference for generic/brown sugar. Prices include VAT and exclude shipping.
No account, receipt or private customer data was collected.

## Validation and delivery

The installer's complete regression set passed, as did the additional inventory,
meal lifecycle, recipe metrics and active-panel contracts. New regression cases
cover a complete multi-ingredient recipe, exact-purchase precedence, unsupported
quantities, country boundaries, disabled automatic lookup, old-reference migration,
retail provenance/expiry, and the real offline variant endpoint. Browser checks cover
card preview concurrency, entry isolation, missing-cost explanations and quantity links.

The v86 installer uses a pinned source commit, preflight tests, a backup, stop/start,
served-panel verification and rollback. It installs the v86 panel at cache key
`2026.9.16.10`. Run it as a standalone script, not by sourcing it in the SSH shell.

Tested runtime commit: `849280cf7e6ee2e2af089f47532301a900f08900`.
