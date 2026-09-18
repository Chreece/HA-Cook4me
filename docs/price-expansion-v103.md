# Offline price expansion v103

Checked 2026-09-17 for Germany/EUR. Two vegetarian retail references bring the offline snapshot to **520 observations: 371 receipt observations and 149 retail references**. One USDA spoon portion and one USDA water density bring the quantity evidence to **123 portions and five densities**, alongside six recipe portions and 18 rough budget groups.

## Catalog coverage

The audit compares published v102 commit `8a61b66263635df350a26e63eefe6079adacdcf7` with v103 across the same **32,163 language/serving variants and 230,483 ingredient occurrences**, without household prices.

| Measure | v102 | v103 | Change |
| --- | ---: | ---: | ---: |
| Occurrences with observed/reference prices | 134,661 | 134,964 | +303 |
| Variants fully covered by observed/reference prices | 5,764 | 5,779 | +15 |
| Occurrences using rough food-group budgets | 41,772 | 41,616 | −156 |
| Unmeasured basic zero allowances | 13,462 | 13,462 | 0 |
| Covered occurrences, including budgets and zero allowances | 189,895 | 190,042 | +147 |
| Complete variants, including budgets and zero allowances | 15,261 | 15,311 | +50 |
| Variants without any observed/reference price | 1,503 | 1,494 | −9 |

The gains are 147 measured-water occurrences, 91 miso/miso-paste occurrences and 65 shimeji occurrences. Counts describe ingredient occurrences and language/serving variants, not unique recipes. Fifty additional complete budgets are distinct from the 15 additional variants fully covered by observed/reference prices. Sixty-one variants still have no usable budget cost.

`price-expansion-v103.json` includes the comparison, changed ingredients and the next 30 reference gaps. Reproduce it with:

```sh
python tools/audit_price_expansion_v103.py --output /tmp/cook4me-v103-audit.json
```

## Product evidence

| Product | Package price | Source |
| --- | ---: | --- |
| Hikari Savoury White plain miso paste | €3.49 / 300 g | [Asian Brand](https://asianbrand.de/products/miso-japanisch-weiss-savoury-white-hikari-300g) |
| Fresh brown shimeji mushrooms | €1.79 / 150 g | [Asian Brand, variant 55554228355420](https://asianbrand.de/products/braune-pilze-shimeji-mushroom-frisch-150g?variant=55554228355420) |

Both are dated representative retail references, including VAT and excluding shipping. Saved household prices remain preferred. Package food weights are used, not the retailer's 340 g and 160 g shipping weights.

The miso lists water, soybeans, rice, salt and alcohol. Other researched miso products contained fish stock and were not selected. Generic miso is represented by this named white paste; prepared soup, powder and dashi-seasoned paste do not receive this reference through new aliases.

For shimeji, the live product API, visible price and matching SKU C039 JSON-LD agree on €1.79. An older indexed copy showed €1.99 and sold out. The dated observation uses the live response, without promising future price or availability. No individual mushroom or unspecified bag weight is inferred.

## Quantity evidence and form checks

Exact rows were checked in the official [USDA SR Legacy CSV dataset](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip):

| Food | Published quantity | FDC / portion ID |
| --- | ---: | --- |
| Miso | 1 tablespoon = 17 g | [172442](https://fdc.nal.usda.gov/food-details/172442/nutrients) / 90629 |
| Drinking tap water | 1 litre = 1,000 g | [173647](https://fdc.nal.usda.gov/food-details/173647/nutrients) / 93025 |

Miso spoonfuls can use the labelled food-specific mass estimate. Several catalog variants, including 337621 and 669773, use hundreds of millilitres or litres of “miso” in soup/stew preparations. The new portion therefore explicitly disables inferred paste density for volume quantities. These rows retain their prior rough-budget status until their prepared form and concentration are resolved. Ordinary food portion density conversions keep their existing behavior.

Measured water in grams/kilograms can now use the existing regional tap-water tariff through the published approximate 1 g/ml relationship. This applies only to water/tap water, not rose water, sauces or arbitrary liquids. Small measured-water costs may round to €0.00, but still carry tariff evidence and known coverage; they are different from an unmeasured basic zero allowance.

No quantities are invented for missing amounts, and recipe display, cooking amounts and nutrition remain unchanged. Unmeasured salt, pepper and water retain their separate zero-budget allowance. The v102 daikon/red-radish separation is retained.

## Runtime and checks

Build `2026.9.17.7` serves the v103 bundle and invalidates price caches with evidence version 103. It includes all v102, v101 and v100 changes, including the responsive header and shared navigation/filter bar.

- Six new backend tests cover package arithmetic, USDA spoon/water conversions, unsupported forms and quantities, date/market/currency boundaries, saved-price priority, persistent cache reuse and six real variants through the translated card/detail endpoint.
- The shipped bundle displays the real €5.48 offline evidence fixture in English, German and Greek, with both retailer links and both USDA links. Invalid source hosts, credentials, protocols and ports are rejected.
- Seven v102 tests and eight v99 zero-allowance tests provide focused regressions.
- Four installer tests cover success, missing/invalid evidence, activation failures and rollback. Staged and installed probes check both new references, miso soup/paste separation and the water conversion. The installer runs the v103 backend tests before swapping files.
- Bundle freshness, Python compilation, shell syntax and whitespace checks are included.

The installer is pinned to the tested runtime in a follow-up commit, with backup and rollback. No live Home Assistant deployment was performed.
