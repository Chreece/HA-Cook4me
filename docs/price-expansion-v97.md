# Offline price expansion v97

Checked 2026-09-17 for Germany/EUR. This batch adds **five retail references** and **four USDA food portions**, bringing the offline evidence to **509 observations** (371 receipt observations and 138 retail references), 120 USDA portions, six recipe portions and four density records.

## Measured catalog coverage

The reproducible audit compares published v96 commit `6e0937fba024575ab7c6c9917aa8a459ce6e6029` with v97. Both use their own identities, conversions and eligible dated references against the same 32,163 language/serving variants and 230,483 ingredient occurrences. Counts are occurrences and variants, not unique foods or recipes.

| Measure | v96 | v97 | Change |
| --- | ---: | ---: | ---: |
| Ingredient occurrences with observed/reference prices | 131,659 | 132,921 | +1,262 |
| Variants fully covered by observed/reference prices | 5,425 | 5,575 | +150 |
| Ingredient occurrences covered, including rough budgets | 175,750 | 176,381 | +631 |
| Variants fully covered, including rough budgets | 11,268 | 11,465 | +197 |
| Variants without any observed/reference price | 1,535 | 1,512 | −23 |

The largest reference gains are leaf gelatine (386 occurrences), sake (157), swede (144), caper (142), mayonnaise (121), peanut butter (101), mirin (95) and wasabi (91). The compact audit in `price-expansion-v97.json` contains changed identities and remaining gaps. Eighty-two variants still lack any usable budget cost. Unspecified amounts remain unresolved.

## Added retail evidence

These are dated representative product prices, with VAT included and shipping excluded. They are not national averages or availability promises.

| Product form | Package price | Source |
| --- | ---: | --- |
| Dr. Oetker pork leaf gelatine | €2.89 / 12 individual sheets | [Piccantino](https://www.piccantino.de/dr-oetker/blattgelatine-12er) |
| Kizakura Junmai Japanese sake, 15% ABV | €4.29 / 180 ml | [Asia4Friends](https://asia4friends.de/japanischer-sake-junmai-kizakura-180ml) |
| Hinode Hon Mirin, 14% ABV | €4.19 / 400 ml | [Asia4Friends](https://asia4friends.de/hon-mirin-14-vol-hinode-400ml) |
| S&B prepared wasabi/horseradish paste | €1.79 / 43 g | [Asia4Friends](https://asia4friends.de/wasabi-paste-sb-43g) |
| Fresh organic swede/rutabaga | €3.69 / 1 kg | [greenist](https://www.greenist.de/frischesortiment-bio-steckrueben-1-kg.html) |

Mirin uses the explicitly titled 400 ml bottle, not the shop's kg-based summary. Wasabi uses the titled 43 g tube, not the rounded 0.04 kg summary. Each stored record retains its URL, date, market, package basis and form notes. Generic catalog wasabi is priced against the named prepared paste; explicit fresh root and powder are not matched. No spoon or centimetre weight is inferred. Sake and mirin remain separate references, and no alcohol-free substitute is assumed.

## Portion evidence and count handling

Four exact records come from the [USDA SR Legacy dataset](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip):

| Food | FDC ID | Portion ID | Published mass |
| --- | ---: | ---: | --- |
| Canned capers, drained | 172238 | 90139 | 1 tbsp = 8.6 g |
| Smooth peanut butter, without salt | 172470 | 90673 | 2 tbsp = 32 g; normalized to 16 g/tbsp |
| Regular mayonnaise | 171009 | 87758 | 1 tbsp = 13.8 g |
| Raw rutabaga | 168454 | 83121 | 1 medium root = 386 g |

Food-specific masses remain labelled estimates. Generic peanut butter uses the disclosed smooth-peanut-butter portion. The existing caper reference is €1.95 per **90 g drained weight**, confirmed on the [dm listing](https://www.dm.de/p/d/3095647/dmbio-kapern); its gross jar content is 150 g. Mayonnaise can bridge a gram amount to the existing volume-priced reference using its published spoon mass and the existing disclosed 15 ml tablespoon convention. Swede counts use the raw medium-root portion; turnip and cooked swede remain separate.

Leaf gelatine now supports explicit sheet/leaf units, provider sheet IDs and small unlabelled counts. Two sheets cost approximately €0.48 against the twelve-sheet pack. The quantity note identifies individual sheets. No gram, packet-size or bloom-strength equivalence is inferred; the reference product is pork gelatine.

Vanilla pod counts now support **saved per-pod user prices**, including provider `UNIT_28`, which can display as French “gousse” or German “Zehe”. This batch adds no automatic vanilla price. Pod counts do not infer seed, teaspoon, packet or gram quantities. Small unlabelled counts follow the existing limit of 20 and are disclosed as estimates. Neither feature changes the stored recipe, cooking quantities or nutrition data.

## Runtime and focused verification

Build `2026.9.17.1` uses panel element `cook4me-recipe-hub-panel-v97` and evidence version 97. Unchanged recipes reuse persistent costs after the initial evidence invalidation; saved user prices remain preferred. Sheet and pod quantity notes support English, German and Greek. Retail links accept the exact reviewed `www.piccantino.de` and `www.greenist.de` HTTPS hosts through the existing URL validation.

- Six backend tests cover the new references, market/currency/date boundaries, portions, sheet/pod counts, incompatible forms, seven real catalog variants through the recipe-cost endpoint, translated card/recipe agreement, manual prices and persistent cache reuse.
- The shipped bundle is exercised in Chromium against the actual eight-ingredient €3.25 preview in `price-expansion-v97-preview.json`, including Greek quantity notes, singular/plural labels, retail/USDA links and misleading URL rejection.
- Four installer tests cover evidence preflight, complete installation, failure handling and rollback. Its new probe checks v97 evidence counts, portions and sheet counts; it runs only `test_price_expansion_v97.py`.
- Bundle freshness, Python compilation, shell syntax and whitespace checks are included.

The v97 installer retains backup and rollback and is pinned to the tested runtime commit in a follow-up commit. No live Home Assistant deployment was performed. Install using the pinned script from the published v97 branch.
