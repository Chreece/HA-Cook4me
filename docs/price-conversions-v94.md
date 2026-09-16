# v94: source quantities and compatible price units

The screenshot recipe, **Sałatka z buraczków, dyni i fety** (variant `848764`, four servings), had two missing amounts and two ingredients falling back to category budgets despite saved prices. v94 recovers the source details for costing and adds food-specific mass/volume conversions.

## Result

The offline DE/EUR fixture in `price-conversions-v94.json` covers all nine ingredients: eight use saved price references and one uses a clearly labelled rough budget. The estimated total is **€9.35**, or **€2.34 per serving**; the saved-price subtotal is €9.31. Quantity conversions remain estimates even where the unit price is observed. These are reference costs, not a store quotation.

| Ingredient | Change | Fixture cost |
| --- | --- | --- |
| Small pumpkin | Source recipe specifies a small pumpkin; a sourced 400 g reference converts the count | ≈ €0.86 |
| Balsamic vinegar | USDA 16 g tablespoon portion converts 20 g to approximately 18.75 ml | ≈ €0.15 |
| Rapeseed oil | FAO density 0.92 g/ml converts 40 g to approximately 43.48 ml | ≈ €0.26 |
| Salt and pepper | Source recipe lists a 1 g allowance for four servings; unknown mixture ratio remains a spice budget | ≈ €0.04 |

The original recipe ingredients and nutrition inputs are unchanged. Source recovery applies only to this reviewed variant when its units/amounts are absent. Measured edits and saved user prices retain precedence. Missing quantities in unrelated recipes remain explicit.

## Evidence

- [Tefal original recipe](https://www.tefal.pl/przepisy/detail/index/source/PRO/id/848764/): one small pumpkin and 1 g salt and pepper to taste, four servings. The seasoning allowance scales with servings and is not represented as an exact salt/pepper ratio.
- [Alnatura small Hokkaido reference](https://www.alnatura.de/de-de/rezepte/suche/hokkaido-suppe-105064/): one small pumpkin, 400 g. Actual size and variety vary; this does not assign 400 g to unspecified pumpkins.
- [Knuspr Hokkaido listing](https://www.knuspr.de/1032-bio-hokkaido-kuerbis-1-stk): €2.15/kg when checked on 2026-09-16, Berlin listing, out of stock. Stored as a per-kilogram price, not a fixed piece price.
- [FAO/INFOODS Density Database](https://www.fao.org/4/ap815e/ap815e.pdf): rapeseed oil at 20 °C, 0.92 g/ml, printed page 11 (PDF page 14).
- [USDA balsamic vinegar, FDC 172241](https://fdc.nal.usda.gov/food-details/172241/nutrients): tablespoon 16 g and teaspoon 5.3 g, SR Legacy portion records 90145 and 90147. Spoon volumes remain approximate.

The snapshot now contains 473 observations, including 102 retail references; 90 USDA portions, four recipe reference portions and two densities are bundled offline. Existing country/currency and freshness rules still apply.

## Display and caching

Ingredient prices now show the quantity conversion or source allowance, with source links in cost details. Pantry percentages receive a home icon and a localized tooltip/accessible label. English, German and Greek text are included.

Pricing evidence version 94 invalidates old totals once. Reopening the same recipe and restoring the persistent server cache reuse the computed result. Card previews and expanded translated recipes produce the same budget total. The inherited v93 job cancellation, filter toolbar and meal-time UI remain included.

## Focused verification

- Five backend tests: actual offline recipe-cost endpoint, screenshot coverage, conversions, scoped recovery, edited amounts, user prices, market boundaries and cache reuse.
- Browser check using the shipped bundle: Greek quantity notes, pantry indicators, detailed sources, repeated painting, missing-amount text and safe link handling.
- Four installer tests: successful pinned installation, missing/invalid evidence preflight, and rollback after activation failures. The installer runs only this build's backend test module and price evidence probe.
- Bundle freshness, Python compilation, shell syntax and whitespace checks.

Build `2026.9.16.18`; panel element `cook4me-recipe-hub-panel-v94`. Installation is performed by `tools/deploy_offline_runtime_v94.sh`, with backup and rollback. No live Home Assistant deployment was performed during these checks.
