# Offline price expansion v102

Checked 2026-09-17 for Germany/EUR. Four vegetarian package references bring the offline snapshot to **518 observations: 371 receipt observations and 147 retail references**. Two new USDA portions bring that evidence set to **122 portions**. The six recipe portions, four densities and 18 rough budget groups are retained.

## Catalog coverage

The reproducible audit compares published v101 commit `b7fd2c9f122fb7c9c009e018a5349fb0df40b05b` with v102 across the same **32,163 language/serving variants and 230,483 ingredient occurrences**, without household prices.

| Measure | v101 | v102 | Change |
| --- | ---: | ---: | ---: |
| Occurrences with observed/reference prices | 134,124 | 134,661 | +537 |
| Variants fully covered by observed/reference prices | 5,749 | 5,764 | +15 |
| Occurrences using rough food-group budgets | 42,278 | 41,772 | −506 |
| Unmeasured basic zero allowances | 13,462 | 13,462 | 0 |
| Covered occurrences, including budgets and zero allowances | 189,864 | 189,895 | +31 |
| Complete variants, including budgets and zero allowances | 15,261 | 15,261 | 0 |
| Variants without any observed/reference price | 1,509 | 1,503 | −6 |

These are ingredient occurrences and language/serving variants, not unique recipes. Most gains replace rough budgets with named product evidence. The final gain is 537 after excluding nine measured daikon occurrences from the new red-radish reference. Sixty-one variants still have no usable budget cost.

`price-expansion-v102.json` records the comparison, changed ingredient identities and next 30 reference gaps. Reproduce it with:

```sh
python tools/audit_price_expansion_v102.py --output /tmp/cook4me-v102-audit.json
```

## New package evidence

All prices below include VAT and exclude shipping. These are dated representative product prices, not national averages or availability promises. Saved household prices remain preferred.

| Product | Package price | Source |
| --- | ---: | --- |
| Bamboo Garden unsweetened coconut cream, 20–22% fat | €2.69 / 400 ml | [Fuchs Gruppe](https://fuchsgruppe.shop/bamboogarden/produkte/kokoscreme-400ml-0.4-liter-dose/) |
| Davert organic dried green split peas | €2.99 / 500 g | [Davert](https://www.davert.de/produkte/halbe-gruene-schaelerbsen-500g) |
| Fresh shiitake mushrooms | €2.49 / 150 g | [Asian Brand](https://asianbrand.de/products/frische-shiitake-pilze-150g) |
| Fresh red radishes without greens | €1.90 / 500 g | [Frische Kontor, selected 500 g variant](https://frische-kontor.de/products/radieschen?variant=51135429935444) |

The coconut cream product contains 91% coconut extract and water. Its price was checked against the matching product price field on the retailer page. Sweetened cream of coconut, coconut butter and powder are not mapped to it.

Split peas use the named green dried variety; there is no cooked-to-dry conversion. Fresh shiitake prices do not apply to dried mushrooms or powder. The shiitake listing was marked sold out when checked, which is recorded in the evidence note.

The radish price uses the explicit 500 g variant, not its 590 g shipping weight. The provider shares identity `M_FOOD_412` between red radish and the Japanese 大根 / Chinese 白蘿蔔 translations. Twelve original Japanese/Chinese variants are scoped to the existing daikon price identity, independently of the UI language. They do not receive the red-radish price or its small piece weight. This changes costing only; recipe display, quantities and nutrition remain unchanged.

## Food-specific quantities

The following exact rows were checked in the official [USDA SR Legacy CSV dataset](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip):

| Food | Source portion | FDC / portion ID |
| --- | ---: | --- |
| Raw shiitake mushrooms | 1 whole piece = 19 g | [169242](https://fdc.nal.usda.gov/food-details/169242/nutrients) / 84500 |
| Raw coconut cream, liquid expressed from grated meat | 1 tbsp = 15 g | [170580](https://fdc.nal.usda.gov/food-details/170580/nutrients) / 86894 |

Whole fresh shiitake counts can use the 19 g average as a labelled estimate, including the existing small implicit-count convention. Japanese units that might represent slices are not treated as whole mushrooms. Coconut cream mass/volume costing uses the food-specific tablespoon row with the existing 15 ml tablespoon convention; it is an estimate, not a claim that every brand has identical density. Neither conversion rewrites recipe amounts or nutrition.

Whole bay-leaf weights remain unresolved: the checked USDA rows describe crumbled spoonfuls. Missing recipe quantities remain unresolved, while unmeasured salt, pepper and water retain v99's separate zero-budget allowance without increasing observed/reference coverage.

## Runtime and verification

Build `2026.9.17.6` serves the v102 bundle and invalidates price caches with evidence version 102. The bundle retains the v100 responsive header and shared navigation/filter bar and all v101 changes. Four reviewed retailer HTTPS hosts are added to the existing evidence-link validation.

- Seven backend tests cover package arithmetic, sourced estimates, unsupported forms and amounts, date/market/currency boundaries, saved-price priority, persistent cache reuse, seven real recipe variants and daikon separation across display languages.
- The actual offline €4.40 evidence fixture renders in English, German and Greek, including all four retailer links and both USDA links. Misleading hostnames, credentials, protocols and ports are rejected.
- The five v101 price tests and eight v99 zero-allowance tests pass as focused regressions.
- Four installer tests cover successful installation, missing/invalid evidence, activation failures and rollback. Staged and installed probes require all four references, both new portions and the updated evidence counts. The installer runs the v102 backend tests before swapping files.
- Bundle freshness, Python compilation, shell syntax and whitespace checks are included.

The installer is pinned to the tested runtime in a follow-up commit and retains backup and rollback. No live Home Assistant deployment was performed.
