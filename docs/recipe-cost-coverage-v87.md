# Cook4me v87: close measured offline price gaps

The v86 snapshot still left most recipes partially priced. This release adds 28
dated reference records, resolves provider identity collisions, and supports
additional reviewed quantity conversions. It also makes the coverage of each
card's subtotal visible as “7/10 ingredients priced”.

## Reproducible comparison

DE/EUR, 16 September 2026, no household prices or internet requests. These are
**language/serving variants**, not unique recipe families. Both versions execute
their own category and quantity rules against their own Open Prices **and**
retail snapshots, applying the same country, currency and 180-day date boundary.

| Across 32,163 variants | v86 | v87 |
|---|---:|---:|
| No cost at all | 6,465 | 2,184 |
| Partially priced | 25,236 | 26,765 |
| Every ingredient priced | 462 | 3,214 |
| Priced food ingredient occurrences, excluding water | 78,396 | 94,440 |
| Priced water occurrences | 0 | 14,748 |

The partial count increases because many previously unpriced recipes now have a
subtotal. Food coverage improves by 20.5% independently of the new water reference.
For the 2,414 German variants, unpriced variants fall from 430 to 159 and complete
estimates rise from 40 to 240.

Run `python tools/audit_recipe_price_coverage_v87.py --as-of 2026-09-16 --output docs/recipe-cost-coverage-v87.json`.
The baseline is commit `d62f438fd0d2b4352ed2a46818e7de748395a3bc`.
The JSON includes every language's results and the largest remaining gaps.

## Recipes in the reported screenshot

| Recipe | v86 priced | v87 priced | Remaining |
|---|---:|---:|---|
| Keksz csokoládé darabokkal | 7/8 | 8/8 | — |
| Makaron w mocno serowym sosie z pieczarkami | 6/11 | 11/11 | — |
| Muhlama-Haferbrei | 3/5 | 5/5 | — |
| Szybkie ciasto makowo-migdałowe | 10/13 | 12/12 | Reviewed “Additionally:” heading excluded from costing |
| Legume și mozzarella la abur | 5/8 | 6/8 | Unspecified salt; mint count has no explicit leaf measure |
| Pesto-Suppe | 4/10 | 7/10 | Bean/noodle form ambiguous; salt amount unspecified |
| Šošovicovo-pórová paštéta | 4/7 | 6/7 | Pepper amount unspecified |

These seven variants are also checked through `offline_recipe_price`, using the
real catalog and shipped evidence. Original cooking quantities and duplicate
source ingredient rows remain intact. The cropped salad title was not identified.

## Evidence and assumptions

The merged snapshot has **405 records: 371 Open Prices observations, 33 retail
references and one utility reference**. The retail JSON retains the product,
price, package basis, date, shop, source URL and explanatory notes for each record.
Regular listed prices are used, excluding membership discounts and delivery.
Knuspr references are explicitly regional to Berlin and surroundings.

Examples of linked primary evidence:

- [dm vegetable stock cubes](https://www.dm.de/p/d/1490263/dmbio-gemuesebruehwuerfel): six 11 g cubes for €0.75; one cube makes 500 ml broth. Cube and prepared-volume references are separate. Powder grams are not treated as liquid broth.
- [Knuspr Parmesan](https://www.knuspr.de/94489-miil-parmigiano-reggiano-dop-24-gereift), [macaroni](https://www.knuspr.de/30952-kitchin-chifferi-no-132), [poppy seeds](https://www.knuspr.de/72159-kitchin-mohnsamen-gemahlen) and [vanilla extract](https://www.knuspr.de/1317-dr-oetker-bourbon-vanille-extrakt).
- [ALDI SÜD Cheddar announcement](https://www.aldi-sued.de/newsroom/alle-pressemitteilungen/marke-und-produkte/2026/aldi-macht-kaese-guenstiger--bis-zu-30-cent-weniger-pro-packung): €2.19 per **175 g** for ALDI SÜD. Its actual publication date, 15 April 2026, is retained; it expires under the normal 180-day rule.
- [Berliner Wasserbetriebe tariff](https://www.bwb.de/de/gebuehren.php): €1.813 per 1,000 litres including VAT. This is a disclosed **regional usage benchmark**, not the user's household tariff; fixed charges and wastewater are excluded. Small amounts can round to €0.00, but the underlying reference is nonzero.
- [FAO/INFOODS Density Database v2](https://www.fao.org/4/ap815e/ap815e.pdf), printed page 13: full-fat crème fraîche at 38% fat, approximately 0.978 g/ml. Fat-content uncertainty is disclosed. No universal grams-to-millilitres assumption is introduced.
- Eight added USDA SR Legacy portions retain food IDs, portion IDs and the original serving weight. Lemon/lime and leek estimates describe edible portions, so they remain approximate purchase-cost references.

Generic cheese uses the named Gouda reference; generic cooking oil uses rapeseed
oil. Frozen vegetable references identify their form. Liquid vanilla and ground
vanilla retain separate volume/mass prices. These are estimates, never exact
household purchases. User-entered and paid-lot prices retain priority.

The provider's `M_FOOD_388` Pepper means black pepper; other “Pepper” identities
do not inherit that price or spoon weight. `M_FOOD_131` Tomato purée means
concentrated tomato paste in the reviewed German/French source labels.

Unspecified seasoning quantities, pinches, ambiguous packs and unsupported
ingredient forms remain partial. No fictional seasoning allowance is added.

## Deployment and checks

v87 uses a fresh frontend bundle scope and cost-cache evidence revision. The
upgrade rebuilds automatic references while preserving manual prices and purchase
history. Offline card previews still avoid network calls and price-store writes.

The standalone installer validates the staged 371 + 34 records, 60 portions and
one density entry before stopping Home Assistant. It probes those same files
again after activation, verifies the served bundle, retains a backup, and restores
the previous integration if activation fails. It keeps the existing 120-second
Docker stop timeout and never clears Home Assistant storage.

Validation covers real screenshot recipes, pepper identity separation, stock
package yield, density sources, regional tariff notes/expiry, migration, native
paid-price priority, browser coverage labels and escaped evidence links. Deployment
simulations execute the installer's actual Python probe, including missing,
invalid and truncated evidence, failed activation and rollback.
