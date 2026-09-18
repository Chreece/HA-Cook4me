# Recipe budget fallback v91

The user requested a universal fallback when the food identity and amount are known. This release adds data-derived budget estimates while preserving observed/saved prices and the existing persistent cache.

## Behavior

1. Use the existing purchase, saved reference or compatible ingredient price first.
2. For the remaining quantity of a matched food, estimate a budget from the median unit price of comparable local foods.
3. Where that group has no compatible data, use the broader local food basket with an explicit low-confidence label.
4. Missing quantities, unknown units, unconfirmed food identities and nonfood catalog entries remain unresolved.

Cards show **Estimated total/subtotal ≈ …**, the number of covered ingredients and the number of rough estimates. Recipe details retain the known-cost subtotal, observed coverage, individual benchmark assumptions and comparison sources. The comparison range is the minimum/maximum spread of source product unit prices, not a confidence interval or a bound on the true ingredient price.

## Data and algorithm

The model uses the existing dated local retail/Open Prices records; this is not a new observed price for an unmatched ingredient. The 18 reviewed peer groups and exact names/categories are in `catalog/price_benchmarks.v1.json`. There is no fuzzy food matching and no currency conversion. Sources must be usable, finite, positive, from the selected shopping country/currency, dated within 180 days and not in the future. Water utility prices and excluded observations do not enter the food basket.

Repeated observations of the same product and unit count only once, using the latest date. The median resists extreme prices; the full min/max spread remains visible. Every estimate retains all selected source IDs and up to four representative links covering the endpoints and median observations. This keeps persisted previews small enough to reuse across page reloads. The source count refers to the whole comparison set; the link summary shows how many representative sources are displayed.

Known grams, millilitres or explicit pieces are used without guessing missing amounts. Existing sourced conversions apply, with edible mass preferred over comparisons between unlike whole pieces. One additional USDA portion covers sun-dried tomatoes: FDC 168567, portion 83340, one dry piece = 2 g. Four dry tomatoes therefore use 8 g of the condiment benchmark, not the price of four whole produce items. This portion is not used to claim that an oil-packed tomato price is a verified dry-tomato price.

Exact purchases remain in their actual currency and only the uncovered fraction gets a fallback. Repeated ingredient rows keep their own amounts. Benchmarks never enter the saved ingredient reference store or become barcode mappings. Turning automatic pricing off disables fallback estimates as well.

## Audit

Germany/EUR, 2026-09-16, empty household inventory. Counts are language/serving variants and ingredient occurrences, not unique recipes or ingredients.

| Measure | Before fallback | With fallback |
|---|---:|---:|
| Ingredient occurrences with a value | 123,465 | 174,615 |
| Recipe variants with every ingredient covered | 3,677 | 11,172 |
| Recipe variants with no value | 1,902 | 82 |

51,150 additional ingredient occurrences receive rough budget estimates. The known-price count remains 123,465; the new combined coverage is 174,615 out of 230,483 occurrences. All matched food entries with a usable amount have either a known price or a budget estimate. The remaining 55,868 gaps comprise 55,721 missing/unsupported quantities or unconfirmed matches and 147 water entries without a compatible tariff unit. These are not priced as free ingredients.

| Screenshot recipe | Known | With fallback | Total |
|---|---:|---:|---:|
| Chicken and cauliflower stew (331197) | 4 | 4 | 7 |
| Curry de tofu et brocolis (826311) | 5 | 5 | 6 |
| Mushroom risotto (252627) | 5 | 6 | 6 |
| Nouilles curry rouge (487446) | 6 | 6 | 7 |
| Okruglice u umaku od rajčice (357993) | 4 | 5 | 10 |
| One-pot-Pasta mit ger. Tofu (317075) | 6 | 6 | 7 |
| Pear and honey couscous (307808) | 4 | 4 | 5 |
| Poulet au curry sucré salé (734674) | 7 | 7 | 8 |
| Risotto alla milanese (816820) | 3 | 4 | 8 |
| Risotto aux asperges (834652) | 6 | 7 | 8 |
| Risotto aux champignons (834656) | 7 | 7 | 8 |
| Směs těstovin s uzeným tofu (287823) | 6 | 6 | 7 |
| Къри със зеленчуци (862912) | 5 | 6 | 7 |
| طاجن الخضراوات الجذرية (341615) | 7 | 7 | 9 |

The mushroom risotto's provider ingredient is “Chestnut”; the fallback follows that catalog identity and labels a nut/seed comparison, without silently changing it to mushrooms. Stock uses a prepared-broth comparison only when its volume is known. Saffron, generic poultry pieces and salt with missing/ambiguous amounts remain unresolved.

## Caching and API

`totalsByCurrency`, `complete` and each row's `coverage` retain their original known-price meaning. New `budgetTotalsByCurrency`, `budgetRangeByCurrency`, `budgetPerServingByCurrency`, `budgetComplete`, `budgetIngredientCount` and `fallbackIngredientCount` expose the separate budgeting result. Each affected row has a `fallbackEstimate` and `budgetCoverage`. This prevents existing consumers from confusing a benchmark with a verified ingredient price.

The derived budget is saved in the same persistent recipe-cost cache as the original cost. The v91 evidence/calculator version invalidates old entries. Market, inventory, recipe amounts, saved references and the automatic-pricing preference remain part of cache validation. Browser previews retain the v90 user/entry separation, bounded cache size, reload reuse, retry behavior and explicit price refresh.

## Validation and installation

All 290 tests across 32 installer regression modules passed. Targeted tests cover peer medians, source deduplication, expiry, market/currency boundaries, observed/manual-price priority, partial purchases, repeated ingredient rows, unit/identity rejection, dry-tomato conversion, live/offline paths, cached budgets and disabling automatic pricing. Browser checks cover estimate/known-cost labels, Greek display, escaped text and source URLs, plus the previous persistent-reload, retry and account-isolation cases.

The v91 installer validates the benchmark file, its 18 groups, all original price evidence, 88 USDA portions, and a real fallback calculation before stopping Home Assistant and again after activation. Backup/rollback and the 120-second Docker stop timeout are retained.

```sh
python tools/audit_recipe_price_fallback_v91.py --output docs/recipe-cost-fallback-v91.json
```
