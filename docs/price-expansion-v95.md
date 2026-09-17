# v95: broader offline price coverage

Adds 20 DE/EUR retail references and food-specific quantity conversions. The bundled snapshot now contains **493 observations**, including **122 retail references**. Eligible receipt observations and saved user prices retain their existing precedence.

## Measured coverage

The audit compares v94 commit `978f4e5511f7d648e4c17909746b3d8973f74ef4` against v95 using the actual ingredient matching and price measurement code. It covers 32,163 language/serving variants and 230,483 ingredient occurrences in the bundled catalog. These are variant counts, not unique recipe counts.

| Measure | v94 | v95 | Change |
| --- | ---: | ---: | ---: |
| Ingredient occurrences with observed/reference prices | 124,005 | 130,546 | +6,541 |
| Variants fully covered by observed/reference prices | 3,799 | 5,359 | +1,560 |
| Ingredient occurrences covered, including rough budgets | 174,897 | 175,750 | +853 |
| Variants fully covered, including rough budgets | 11,195 | 11,268 | +73 |
| Variants without any observed/reference price | 1,883 | 1,538 | −345 |

Most improvements replace broad category budgets with named food price references. Published spoon, leaf, sprig and piece weights also resolve previously missing quantities. Missing amounts, unknown bunch sizes and unsupported ingredient identities remain explicit; 82 variants still have no usable budget cost. Full compact results and the largest remaining gaps are in `price-expansion-v95.json`.

## Added evidence

The new references cover tahini, buckwheat, millet, baking soda, sesame, icing sugar, fennel, celeriac, butternut squash, savoy/green cabbage, Brussels sprouts, bay leaves, peanut oil, chicory, chard, green bell pepper, plain fresh cheese, tomato coulis/passata, brown rice and turnip. Each entry in `catalog/retail_prices.v1.json` preserves its product URL, package basis, country, date and source notes.

Sources checked on 2026-09-16 include [dm tahini](https://www.dm.de/p/d/3064622/dmbio-sesammus-tahin), [Knuspr fennel](https://www.knuspr.de/78004-fenchel-1-stk), [FriFro peanut oil](https://frifro.de/lebensmittel_shop_4/fette_oele/fette_oele/mazola_erdnussoel_500ml.html) and [Trübenecker turnip](https://www.truebenecker.de/products/bio-mairuben-ohne-blatter-1kg). These are German retail reference prices, not availability promises or a quotation. Seasonal/out-of-stock listings are identified in their notes. The chard reference normalizes the regular listed €2.60 per approximately 400 g to €6.50/kg and excludes the personal discount shown on that listing.

- **19 additional USDA portions** (109 total): spoon weights, medium vegetable counts, and specific herb leaf/sprig weights. Records retain their exact FDC and portion identifiers from the [USDA SR Legacy dataset](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip).
- **Two additional recipe portions** (six total): ground cumin and garam masala, from the published gram/spoon quantities in [Dairy Farmers of Ontario's butter chicken recipe](https://new.milk.org/discover-dairy/recipes/winter-comfort-butter-chicken/).
- **Two additional densities** (four total): plain unsweetened yoghurt, 1.031 g/ml, and peanut oil at 15.6 °C, 0.92 g/ml, from the [FAO/INFOODS Density Database](https://www.fao.org/4/ap815e/ap815e.pdf), printed page 11.

Food-specific conversions remain labelled estimates with evidence links. Product size, packing, grind and brand vary. The plain fresh cheese reference uses plain cream cheese as its representative product; individual fromage frais products can differ. Greek/strained yoghurt, tomato paste, pickled turnip and unspecified herb bunches do not inherit these new conversions. A count of bay leaves still has no verified whole-leaf weight in this change.

## Display and cache behavior

Leaf and sprig amounts have English, German and Greek labels with singular/plural forms. Cost details allow the new primary recipe source URL through the existing strict source-link validation. A seven-ingredient offline preview in `price-expansion-v95-preview.json` has an estimated total of €2.77, with all seven ingredients covered by references.

Evidence version 95 invalidates previous totals once. Reopening an unchanged recipe and restoring the persistent server cache reuse the calculated result. Changing a saved user price invalidates the relevant cache and applies that price. The inherited job cancellation, filter toolbar and meal-time UI remain included.

## Focused verification

- Five backend tests exercise the new references, market boundaries, food-specific conversions, seven real catalog variants through the recipe-cost endpoint, translated recipes, saved user prices and persistent cache reuse.
- The browser check loads the shipped bundle and checks the actual offline preview, Greek quantity notes, all three unit-label languages, source links and rejection of misleading URLs.
- Four installer scenarios cover the pinned installation, missing/invalid snapshot preflight and rollback. The installer runs only this build's backend test module and evidence probe.
- Bundle freshness, Python compilation, shell syntax and whitespace checks.

Build `2026.9.16.19`; panel element `cook4me-recipe-hub-panel-v95`. The pinned `tools/deploy_offline_runtime_v95.sh` installer includes backup and rollback. No live Home Assistant deployment was performed during verification.
