# Recipe cost coverage v90 — 2026-09-16

This release addresses the latest screenshot and repeated price calculation on page reopening. Germany/EUR audit, with no household prices or inventory. Counts are language/serving variants and ingredient occurrences, not unique recipes or unique foods.

## Coverage

| Measure | v89 | v90 |
|---|---:|---:|
| Priced food ingredient occurrences | 106,862 | 108,717 |
| Priced water occurrences | 14,748 | 14,748 |
| Variants with no priced ingredients | 1,944 | 1,902 |
| Complete variants | 3,686 | 3,677 |
| Partial variants | 26,533 | 26,584 |

There are 1,855 additional priced food occurrences. The screenshot improves from 62/103 to 75/103 ingredients. Water coverage is unchanged. Complete counts fall by nine overall because the incorrectly tagged Open Prices observation 307878 (47 g seasoning mix) is excluded from generic chicken-meat estimates. Keeping that mistaken match would falsely inflate coverage. Its exact barcode price remains usable, and live refresh applies the same exclusion.

| Screenshot recipe | v89 | v90 | Remaining gaps |
|---|---:|---:|---|
| Chicken and cauliflower stew (331197) | 4/7 | 4/7 | Poultry — amount missing/unsupported; Mixed herbs — amount missing/unsupported; Salt — amount missing/unsupported |
| Curry de tofu et brocolis (826311) | 5/6 | 5/6 | Salt — amount missing/unsupported |
| Mushroom risotto (252627) | 5/6 | 5/6 | Chestnut — price/unit missing |
| Nouilles curry rouge (487446) | 5/7 | 6/7 | Curry — amount missing/unsupported |
| Okruglice u umaku od rajčice (357993) | 4/10 | 4/10 | Pike dumplings — amount missing/unsupported; Sun-dried tomatoes (optional) — price/unit missing; Mixed herbs — amount missing/unsupported; Ketchup — amount missing/unsupported; Sugar — amount missing/unsupported; Oil — amount missing/unsupported |
| One-pot-Pasta mit ger. Tofu (317075) | 3/7 | 6/7 | Salt — amount missing/unsupported |
| Pear and honey couscous (307808) | 4/5 | 4/5 | Cinnamon — amount missing/unsupported |
| Poulet au curry sucré salé (734674) | 5/8 | 7/8 | Salt — amount missing/unsupported |
| Risotto alla milanese (816820) | 3/8 | 3/8 | Stock — price/unit missing; Saffron — amount missing/unsupported; Bone marrow — amount missing/unsupported; Parmesan — amount missing/unsupported; Salt — amount missing/unsupported |
| Risotto aux asperges (834652) | 6/8 | 6/8 | Green asparagus — price/unit missing; Salt — amount missing/unsupported |
| Risotto aux champignons (834656) | 7/8 | 7/8 | Salt — amount missing/unsupported |
| Směs těstovin s uzeným tofu (287823) | 5/7 | 6/7 | Salt — amount missing/unsupported |
| Къри със зеленчуци (862912) | 5/7 | 5/7 | Radish — price/unit missing; Salt — amount missing/unsupported |
| طاجن الخضراوات الجذرية (341615) | 1/9 | 7/9 | Herb bundle — amount missing/unsupported; Cinnamon — amount missing/unsupported |

## New evidence and matching

Seven dated German retail references bring the combined snapshot to 471 records (371 Open Prices, 99 retail, one water tariff). Each retains a named product, source link, package basis, observation date and limitations. Regular prices exclude personal/member discounts. Shipping is excluded.

| Product reference | Price / basis | Primary source |
|---|---|---|
| dmBio raisins | €2.95 / 500 g | [Retail listing](https://www.dm.de/p/d/1447524/dmbio-trockenfruechte-rosinen) |
| KITCHIN organic whole-wheat fusilli | €0.85 / 500 g | [Retail listing](https://www.knuspr.de/en-DE/30958-kitchin-organic-durum-whole-wheat-semolina-pasta) |
| Avril cooked flageolet beans | €4.12 / 530 g | [Retail listing](https://www.gourmet-versand.com/de/article24235/flageolets-bohnenkerne-gegart-800-g.html) |
| Watzkendorf organic raw beetroot | €3.79 / 1000 g | [Retail listing](https://www.knuspr.de/90417-watzkendorf-bio-rote-bete-wiegeware) |
| Ludwig fresh Jerusalem artichoke | €0.69 / 100 g | [Retail listing](https://ludwigs.shop/produkt/topinambur/) |
| Ludwig fresh parsnips | €1.99 / 500 g | [Retail listing](https://ludwigs.shop/product-category/gemuese/) |
| MEINE METZGEREI raw chicken breast fillet | €6.79 / 600 g | [Retail listing](https://www.aldi-sued.de/produkt/meine-metzgerei-haehnchen-brustfilet-600-g-000000000000211427) |

47 exact preparation aliases connect reviewed descriptions such as peeled/chopped onion or sliced carrot to existing food references. There is no fuzzy substring matching. Four exact ingredient labels that explicitly say “Tablespoon of …” recover the unit only; a missing numeric quantity remains missing. Original cooking/device ingredients are not modified.

The Arabic root-vegetable tagine now uses raw beetroot (separate from cooked vacuum-packed beetroot), USDA 82 g per beet and an explicitly labelled Alnatura 80 g parsnip estimate. There are 87 USDA portion rows and three other sourced portion rows; density evidence remains separate. The [Alnatura recipe](https://www.alnatura.de/de-de/rezepte/suche/linsen-wurzelgemuese-braten-106601/) supplies the parsnip estimate, not USDA.

The tofu-pasta correction is limited to Czech variants 287823–287825 and German variants 317074–317076. The [Czech recipe](https://www.tefal.cz/recepty/detail/index/source/PRO/id/287823/) specifies tofu cream and cooked flageolet beans; the [German recipe](https://www.krups.at/rezepte/detail/PRO/One-pot-Pasta%2Bmit%2Bger%2BTofu/1018279) confirms 200 ml tofu cream. Its reviewed flageolet identity is matched to the same cooked preparation. The beans reference uses the 530 g drained weight, not the can's 800 g gross weight. Generic “Bean” or “Tofu” elsewhere does not acquire these forms.

No price is invented for unspecified salt amounts, an unlabelled spoon, a herb bundle, generic poultry pieces, ambiguous chestnuts, or green asparagus using a white-asparagus reference. A water-only result explicitly says food costs are unavailable instead of suggesting a €0.00 food subtotal.

## Persistent previews and request recovery

Offline cards previously called the calculator directly and retained results only in a WeakMap. They now use Home Assistant's persistent recipe-cost cache, with stable local-evidence fingerprints. Repeated preview calls return `costCacheHit: true`; a fresh cache instance can reuse saved results without calling the calculator.

The browser persists up to 100 previews, bounded to approximately 1.5 million characters, per Home Assistant origin, user and integration entry. One settings request validates a SHA-256 token over current price references, inventory, market/automatic-price settings, evidence version and UTC date. A matching recipe payload reuses its preview after reload without a recipe-cost request. Validation is coalesced for one minute within a page, and saved previews expire within 24 hours or at the next UTC date. Changed recipe amounts/servings, account, entry, market, inventory, reference prices or release evidence invalidate the applicable cache. Explicit “Update recipe prices” bypasses saved previews. Unavailable browser storage falls back to normal requests.

Failed card requests retry twice, with three active preview requests maximum. Persistent failures show a retry button. A changed payload during a request is requeued, and stale responses cannot repaint another account/entry. Water-only badges and the missing-ingredient explanation remain explicit.

## Validation and deployment

The installer checks all evidence files and exact pinned-release counts before stopping Home Assistant, and again after activation. It retains the previous integration, waits up to 120 seconds for Docker stop and rolls back failed activation.

All 280 tests across 31 installer regression modules passed. They cover the catalog, offline recipes, product capture, dietary behavior, pricing, migration and screenshot variants. Browser checks include a real reload with zero recipe-cost requests, evidence/user invalidation, bounded request concurrency, retry recovery, changed payloads and water-only labels. All six installer test methods passed, including success, missing/truncated evidence, incorrect config mounts and rollback scenarios.

Reproduce the eligibility audit:

```sh
python tools/audit_recipe_price_coverage_v90.py --as-of 2026-09-16 --output docs/recipe-cost-coverage-v90.json
```
