# Offline price expansion v96

Checked 2026-09-16 for Germany/EUR. This batch adds **11 retail references** and **seven USDA food portions**, bringing the offline evidence to **504 observations** (371 receipt observations and 133 retail references), 116 USDA portions, six recipe portions and four density records.

## Measured catalog coverage

The reproducible audit compares v95 commit `02f32ba39784453819547aef0eace031f0e22d02` with v96. Both use their own identities, conversions and eligible dated references against the same 32,163 language/serving variants and 230,483 ingredient occurrences. Counts are occurrences and variants, not unique foods or recipes.

| Measure | v95 | v96 | Change |
| --- | ---: | ---: | ---: |
| Ingredient occurrences with observed/reference prices | 130,546 | 131,659 | +1,113 |
| Variants fully covered by observed/reference prices | 5,359 | 5,425 | +66 |
| Ingredient occurrences covered, including rough budgets | 175,750 | 175,750 | 0 |
| Variants fully covered, including rough budgets | 11,268 | 11,268 | 0 |
| Variants without any observed/reference price | 1,538 | 1,535 | −3 |

The gain replaces rough budgets with sourced references. It does not resolve unspecified amounts. The largest gains are fish sauce (325 occurrences), salmon (293), green lentil (136), fresh goat cheese (134), dried farfalle (92) and nutmeg (90). The compact audit in `price-expansion-v96.json` contains every changed identity and the remaining gaps. Eighty-two variants still lack any usable budget cost.

## Added retail evidence

These are dated representative product prices, not national averages or availability promises. VAT is included and shipping excluded. Knuspr references are from the Berlin-area listing; regional prices may differ.

| Product form | Package price | Source |
| --- | ---: | --- |
| Fresh tarragon | €1.49 / 15 g | [Knuspr](https://www.knuspr.de/851-estragon) |
| Ostmann dried tarragon leaves | €2.49 / 9 g | [Knuspr](https://www.knuspr.de/31988-ostmann-estragon-gerebelt) |
| Ostmann ground nutmeg | €2.99 / 35 g | [Knuspr direct product listing](https://www.knuspr.de/4786-ostmann-muskatnuss-gemahlen) |
| Ostmann whole nutmeg | €2.29 / 2 pieces | [Knuspr](https://www.knuspr.de/4787-ostmann-muskatnuesse) |
| Picandou fresh goat cheese | €4.79 / 80 g | [Knuspr](https://www.knuspr.de/en-DE/17455-picandou-ziegenfrischkaese) |
| Ostmann whole allspice | €2.49 / 25 g | [Knuspr](https://www.knuspr.de/31998-ostmann-piment-ganz) |
| Thanh Ha 38N fish sauce | €7.79 / 500 ml | [Asia4Friends](https://asia4friends.de/fischsauce-38n-thanh-ha-500ml) |
| TRS dry green lentils | €2.49 / 500 g | [Asia4Friends](https://asia4friends.de/gruene-linsen-trs-500g) |
| GOLDEN SEAFOOD plain frozen salmon fillets | €4.99 / 250 g | [ALDI SÜD](https://www.aldi-sued.de/produkt/golden-seafood-lachsfilets-250-g-000000000000191385) |
| Barilla Collezione dried farfalle | €1.49 / 500 g | [ALDI SÜD](https://www.aldi-sued.de/produkt/barilla-collezione-farfalle-500-g-000000000000543569) |
| Ostmann dried dill tips | €2.79 / 25 g | [Knuspr](https://www.knuspr.de/en-DE/4806-ostmann-dill-tips) |

The farfalle listing is a promotion from 2026-08-28 with regional/limited stock. The nutmeg price is taken from its direct product page; recommendation tiles can show a different price. Each stored record retains its URL, date, market, package basis, form and availability notes.

## Portion evidence and form boundaries

Seven exact records come from the [USDA SR Legacy dataset](https://fdc.nal.usda.gov/fdc-datasets/FoodData_Central_sr_legacy_food_csv_2018-04.zip):

| Food | FDC ID | Portion IDs | Published masses |
| --- | ---: | --- | --- |
| Dried tarragon leaves | 170937 | 87574, 87575 | 1 tsp = 0.6 g; 1 tbsp = 1.8 g |
| Dried dill weed | 171322 | 88433, 88434 | 1 tsp = 1 g; 1 tbsp = 3.1 g |
| Ground nutmeg | 171326 | 88441, 88442 | 1 tsp = 2.2 g; 1 tbsp = 7 g |
| Ready-to-serve fish sauce | 174531 | 94526 | 1 tbsp = 18 g |

Food-specific spoon masses are labelled quantity estimates. Fish sauce can use the published spoon mass and the existing disclosed 15 ml tablespoon convention to bridge grams and a volume-priced bottle. Generic nutmeg spoon amounts use the disclosed ground-nutmeg reference. Explicit whole nutmeg has no ground-spoon conversion; whole-nut counts use the two-piece package directly.

Fresh herbs never inherit dried-herb spoon masses. Allspice has a whole-spice mass price but no inferred berry weight or ground-spoon conversion. Fillet counts do not acquire an assumed weight. Cooked/canned lentils, cooked farfalle and smoked salmon remain separate forms. Several newly supported explicit dried-herb names improve ad hoc recipes without increasing this catalog's measured coverage. Miso paste versus broth and ambiguous stock quantities remain deferred.

## Runtime and focused verification

Build `2026.9.16.20` uses panel element `cook4me-recipe-hub-panel-v96` and evidence version 96. Unchanged recipes reuse persistent costs after the initial evidence invalidation; saved user prices remain preferred. Retail source links now accept the exact reviewed `asia4friends.de` HTTPS host through the existing URL validation.

- Five backend tests cover all eleven references, market/currency boundaries, new portions, incompatible forms, seven actual catalog variants through the recipe-cost endpoint, translated recipe/card agreement, saved prices and persistent cache reuse.
- The shipped bundle is exercised in Chromium against the real six-ingredient €2.45 preview in `price-expansion-v96-preview.json`, including Greek quantity notes, inherited unit labels, retail/USDA links and misleading URL rejection.
- Four installer tests cover staged evidence checks, installation, failure handling and rollback; the installer runs only `test_price_expansion_v96.py` and its evidence probe.
- Bundle freshness, Python compilation, shell syntax and whitespace checks are included.

The v96 installer retains backup and rollback and is pinned to the tested runtime commit in a follow-up commit. No live Home Assistant deployment was performed. Install using the pinned script from the published v96 branch.
