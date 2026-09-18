# Cook4me v92 price optimization

Offline card pricing used `ingredient_choices('en')`, a display list that groups source identities and removes preparation text. It omitted 8,068 of the full catalog's 11,748 IDs (including excluded/non-food entries) and simplified another 902 names. Costing now reads the authoritative ingredient table already returned by the warmed release catalog. This preserves reviewed food classification, source IDs, preparation names and measurement-bearing labels. It avoids rebuilding the display picker for each cost request.

The critical difference is real endpoint coverage, not merely adding references to a price file. The Croatian dried-tomato identity now reaches the existing sourced piece conversion and budget fallback; the Arabic beetroot retains its preparation alias and sourced piece weight.

## Measured coverage

Market DE/EUR, 2026-09-16. Counts are **32,163 language/serving variants**, not unique recipes, and **230,483 ingredient occurrences**. No household purchase/manual prices are included. The baseline reproduces v91's display-catalog lookup with enriched recipe rows; the new side uses v92 source identities, quantities and evidence. Earlier audits used the full catalog on both sides and therefore missed the live display-list regression.

| Metric | Actual v91 lookup | v92 lookup |
|---|---:|---:|
| Ingredient occurrences with price references | 123,489 | 123,657 |
| Ingredient occurrences with labelled budget fallbacks | 40,458 | 51,238 |
| Covered ingredient occurrences | 163,947 | 174,895 |
| Variants with every ingredient covered | 9,951 | 11,194 |
| Variants without any usable cost | 146 | 82 |

That is 10,948 additional covered ingredient occurrences and 1,243 additional fully covered variants. Most of the gain is a **rough budget fallback**, not a newly observed ingredient price.

| Screenshot recipe | Before | After |
|---|---:|---:|
| Nouilles curry rouge | 6/7 | 7/7 |
| Okruglice u umaku od rajčice | 4/10 | 5/10 |
| Risotto aux asperges | 7/8 | 7/8 |
| طاجن الخضراوات الجذرية | 6/9 | 7/9 |

The asparagus recipe still has one unquantified ingredient, but its asparagus now uses a product reference instead of the vegetable benchmark. The remaining salt, pepper, herb bundles and other ambiguous quantities remain visibly incomplete.

## Additional corrections

- [Moulinex's red-curry noodles](https://www.moulinex.fr/recette/detail/PRO/nouilles-curry-rouge/2385359) specifies a tablespoon of red curry paste and half an onion. Costing restores those details only for reviewed variant 487446 when its original unit is missing. Cooking/device data and explicitly measured edits remain unchanged. The existing paste product and published spoon mass can now be used.
- Added a [Knuspr green-asparagus reference](https://www.knuspr.de/12094-spargel-gruen-bund): EUR 5.99 per 450 g, Berlin listing observed 2026-09-16. Retail references now total 101; combined evidence totals 472. Regional/seasonal variation and evidence expiry still apply.
- Recognizes explicit German/French spoon labels and explicit localized piece labels, plus a small reviewed list of ingredient names containing “tablespoons”. Generic spoons, chunks, pinches and unspecified amounts are not assigned a fabricated standard size.
- Cache evidence/calculator revisions move to 92 so the previous incomplete results are invalidated once. Repeated calls and reconstructed cache instances reuse the persisted result; browser reload uses the validated local cache without new recipe-cost requests.
- Shorter English/German/Greek budget badges keep the amount and covered count visible; full estimate counts, ranges and sources remain in the accessible description and cost detail.

## Build-specific validation

Five focused pricing/cache tests exercise all 14 screenshot variants through the actual WebSocket handler, with both ID-only requests and displayed ingredient payloads, repeat/cache reuse, scoped recipe corrections, translated units and user-price priority. Ten existing benchmark tests cover the fallback calculations affected by the new identity matches. The browser check covers price badges, persistence, retries and evidence invalidation. Installer checks cover successful activation, missing/invalid price evidence and rollback.

The installer runs only `test_price_optimization_v92.py` and `test_price_fallback_v91.py`, rather than the previous 32 historical test modules. Required price files and counts are validated before stopping Home Assistant and again after activation. Backup/rollback and the 120-second graceful Docker stop are retained.

Reproduce coverage with `python tools/audit_price_optimization_v92.py --output docs/price-optimization-v92.json`.
