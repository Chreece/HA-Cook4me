# Cook4Me v109: weekly totals and shared filters

Build `2026.9.17.13` is cumulative from v108.

The weekly view previously displayed a historical consumption table underneath the planned meals. Its cost heading also reused saved totals from the older cost path, while recipe cards calculated newer local estimates. The new summary covers the same seven HA-local dates and the same visible meals as the plan.

## Behavior

- Daily and weekly summaries show meal count, energy, protein, carbohydrate, fat, saturated fat, sugars, fibre, salt, sodium and cost. Nutrients cover the quantities in each planned recipe, matching the full-recipe cost shown by the cards. Per-serving values are multiplied only when the recipe's serving count is known. Leftovers retain their allocated nutrition and cost.
- Missing values remain unavailable, genuine zero values remain zero, and estimated or incomplete values are labelled. Price sums use the cards' budget totals and preserve separate currencies. Dietary replacements do not silently change the original recipe's nutrient or price evidence.
- Opening a saved plan recalculates prices from the same local evidence used by cards. Current reviewed ingredient nutrition is refreshed from the original quantities. A card price refresh updates both the daily and weekly summaries without replacing the recipe cards.
- The calendar settings button, its separate dialog, detached settings markup and handlers were removed. The right-hand shared controls apply to plan generation, regeneration, the displayed saved plan and its shopping requirements. Existing saved meals are not deleted when filters hide them.
- Shared meal categories control generation instead of the obsolete separate meal schedule. Shared price limits now use the same local price references and measurement preparation as card estimates. They still require complete known price coverage, as described by the shared filter.
- Responses for a previous account, device or filter selection cannot replace the current weekly view. Failed reads stop automatic retries and offer a Retry button.
- The desktop summary is a table. On narrow screens each day becomes a labelled block. Dates, nutrient headings and messages follow Greek, German or English UI language.

The historical consumption API remains available separately. The existing household lot-price editor still represents entered household stock; it is not a second global price catalog.

## Validation

Eight focused Python tests cover actual catalog card/weekly price agreement, edited purchase prices, shared filtering without deletion, leftover accounting, generation slots, cost limits, the production state function and filtered shopping. Weekly variety, rolling dates, meal lifecycle, diet profiles and price regression tests pass.

Chromium exercises the real shared-filter Apply button, Generate, clearing a meal, delayed responses, retry recovery, live price updates, missing/partial/zero nutrient values and Greek/German/English mobile and desktop layouts. Screenshots of the summary were reviewed. The header/navigation and foreign-language Send checks run against the v109 bundle.

The installer includes the new weekly tests, retains its backup/rollback behavior and verifies the exact served frontend bundle. Home Assistant and cloud calls are simulated in automated checks; this work does not change v108's unresolved firmware-crash status.

Published runtime: `b2b1fd26e4d4c6ce27551856a539dd4493d55450` on `cook4me-weekly-summary-v109`. The published tree matches the tested local source: `a851dd1e1ae999bf2da4663204adf0725c2c96b4`.
