# Cook4me v88 — expanded offline prices

Checked 16 September 2026 for the German EUR market. Adds 48 dated retail observations, bringing the bundled total to 453 (371 Open Prices observations, 81 retail references and one regional water tariff). Nine additional USDA spoon portions bring the reviewed portion table to 69 entries.

Frequent gaps now covered include spring onions, fresh herbs, sesame oil, limes, sweet potatoes, chopped tomatoes, breadcrumbs, cocoa, quinoa, bulgur, ricotta, mascarpone and prepared poultry/beef/veal stocks. Exact aliases also connect dried pasta to the explicitly disclosed dry macaroni reference. Original cooking quantities are unchanged.

## Measured coverage

The audit executes each version's own category and quantity rules against the same release catalog. Baseline: v87 commit `866252ba5ef03734c17afa5cf601ae9fbd9979a5`. Counts are **language and serving variants**, not distinct recipe families; food ingredient counts are occurrences across those variants. There are 32,163 variants, including 2,414 German variants.

| Measure | v87 | v88 | Change |
| --- | ---: | ---: | ---: |
| All catalogs: priced food ingredients | 94,440 | 103,647 | +9,207 |
| All catalogs: complete variant totals | 3,214 | 3,559 | +345 |
| All catalogs: partial variant totals | 26,765 | 26,614 | -151 |
| All catalogs: variants with no cost | 2,184 | 1,990 | -194 |
| German catalog: priced food ingredients | 7,982 | 8,837 | +855 |
| German catalog: complete variant totals | 240 | 270 | +30 |
| German catalog: partial variant totals | 2,015 | 1,995 | -20 |
| German catalog: variants with no cost | 159 | 149 | -10 |

The gain is 9,207 priced food ingredient occurrences (+9.75%). Water coverage is unchanged at 14,748; it contributes none of this increase. Many recipes still have partial costs because they lack amounts, use unsupported units or require more specific price evidence. All seven previously reported screenshot examples retain their v87 coverage.

Reproduce with:

```sh
python tools/audit_recipe_price_coverage_v88.py --as-of 2026-09-16 --output docs/recipe-cost-coverage-v88.json
```

The machine-readable report is [recipe-cost-coverage-v88.json](recipe-cost-coverage-v88.json).

## Evidence and boundaries

All added prices have source URLs, named products, country, date and package basis. Retail references are estimates for the named variety and region; household/manual purchase prices retain priority. Public observations expire after 180 days. Knuspr references use its Berlin-area listing; Dallmayr's spring onions are a Munich-area premium retailer reference. Promotional/member discounts are excluded where a regular price is shown.

- Spring onions: €1.90 for a stated 130 g bunch. One onion is never equated with one bunch; the existing disclosed USDA 15 g portion may estimate a single onion.
- Fresh and dried herbs have separate categories and quantities. USDA records support the new chive, rosemary, thyme and cocoa spoon conversions.
- Prepared stock prices accept explicit liquid quantities. Powder, cubes and ambiguous spoon measures remain unpriced by these liquid references.
- Capers use the retailer's explicit 90 g drained weight. Chopped tomatoes include their tomato juice.
- Ground almond pricing is retained as a dated listing reference with an explicit out-of-stock note. Ground almonds and defatted almond flour are not equated.
- Missing quantities, ambiguous pepper/stock names, pinches and unspecified bunches remain missing; no price or amount is invented.

## Added retail observations

The linked retail pages were checked on 2026-09-16. VAT is included; delivery is excluded.

| Named reference product | Price | Basis | Retail source |
| --- | ---: | --- | --- |
| Fresh flat-leaf parsley | €1.89 | 200 g | [Knuspr](https://www.knuspr.de/15110-petersilie-glatt) |
| Fresh chives | €0.99 | 15 g | [Knuspr](https://www.knuspr.de/849-schnittlauch) |
| Fresh dill | €1.99 | 100 g | [Knuspr](https://www.knuspr.de/15100-dill) |
| Fresh basil | €1.59 | 15 g | [Knuspr](https://www.knuspr.de/15084-basilikum) |
| Fresh rosemary | €1.29 | 15 g | [Knuspr](https://www.knuspr.de/855-rosmarin) |
| Fresh thyme | €1.29 | 15 g | [Knuspr](https://www.knuspr.de/857-thymian) |
| Fresh sage | €1.29 | 15 g | [Knuspr](https://www.knuspr.de/856-salbei) |
| Fresh oregano | €1.29 | 15 g | [Knuspr](https://www.knuspr.de/854-oregano) |
| BIO lime | €0.75 | 1 pcs | [Knuspr](https://www.knuspr.de/20751-bio-limette-1-stk) |
| SanLucar limes, four-fruit tray | €2.29 | 240 g | [Knuspr](https://www.knuspr.de/30087-sanlucar-limetten-4er-schale) |
| Sweet potato | €3.99 | 1000 g | [Knuspr](https://www.knuspr.de/3366-suesskartoffel-1-stk) |
| Lauchzwiebel / spring onion | €1.90 | 130 g | [Dallmayr](https://www.dallmayr-versand.de/p/lauchzwiebel-2669BD/) |
| dmBio toasted sesame oil | €3.75 | 250 ml | [dm Germany](https://www.dm.de/p/d/1714605/dmbio-sesamoel) |
| dmBio rice vinegar | €2.25 | 145 ml | [dm Germany](https://www.dm.de/p/d/1639876/dmbio-reisessig-mild-saeuerlich) |
| dmBio walnut oil | €5.45 | 250 ml | [dm Germany](https://www.dm.de/p/d/3065041/dmbio-walnussoel) |
| dmBio ghee / clarified butter | €4.45 | 180 g | [dm Germany](https://www.dm.de/p/d/1469719/dmbio-ghee-geklaerte-butter) |
| dmBio ground Ceylon cinnamon | €1.85 | 50 g | [dm Germany](https://www.dm.de/p/d/1666918/dmbio-ceylon-zimt) |
| dmBio dried Italian herb mix | €1.85 | 35 g | [dm Germany](https://www.dm.de/p/d/1666949/dmbio-gewuerzmischung-italienische-kraeuter) |
| dmBio nutritional yeast flakes (wheat-based) | €3.45 | 100 g | [dm Germany](https://www.dm.de/p/d/3111758/dmbio-hefeflocken-auf-weizenbasis) |
| dmBio dry quinoa | €2.85 | 500 g | [dm Germany](https://www.dm.de/p/d/1570746/dmbio-quinoa) |
| dmBio dry bulgur wheat | €1.35 | 500 g | [dm Germany](https://www.dm.de/p/d/1454920/dmbio-bulgur) |
| koawach unsweetened baking cocoa powder | €2.95 | 100 g | [dm Germany](https://www.dm.de/p/d/3081979/koawach-kakao-zum-backen) |
| dmBio corn semolina / dry polenta | €1.15 | 500 g | [dm Germany](https://www.dm.de/p/d/1446512/dmbio-maisgriess-polenta) |
| dmBio gluten-free rice flour | €2.75 | 500 g | [dm Germany](https://www.dm.de/p/d/1431385/dmbio-reismehl-glutenfrei) |
| dmBio chickpea flour | €1.75 | 300 g | [dm Germany](https://www.dm.de/p/d/1590092/dmbio-kichererbsenmehl) |
| dmBio wholemeal buckwheat flour | €1.75 | 500 g | [dm Germany](https://www.dm.de/p/d/1446511/dmbio-buchweizenmehl-vollkorn-glutenfrei) |
| dmBio spelt semolina | €2.45 | 500 g | [dm Germany](https://www.dm.de/p/d/1446486/dmbio-dinkel-griess) |
| dmBio plain chopped tomatoes in tomato juice | €0.65 | 400 g | [dm Germany](https://www.dm.de/p/d/1440255/dmbio-tomatenstuecke-natur) |
| dmBio virgin coconut oil | €2.85 | 300 ml | [dm Germany](https://www.dm.de/p/d/1544928/dmbio-kokosoel-nativ) |
| dmBio Aceto Balsamico di Modena IGP | €2.45 | 500 ml | [dm Germany](https://www.dm.de/p/d/3143620/dmbio-aceto-balsamico-di-modena-igp) |
| dmBio apple cider vinegar | €1.55 | 750 ml | [dm Germany](https://www.dm.de/p/d/1470124/dmbio-apfelessig) |
| dmBio garam masala | €1.95 | 60 g | [dm Germany](https://www.dm.de/p/d/1435233/dmbio-gewuerzmischung-garam-masala) |
| LEBENSBAUM dried herbes de Provence | €2.95 | 30 g | [dm Germany](https://www.dm.de/p/d/3064302/lebensbaum-gewuerzmischung-kraeuter-der-provence) |
| dmBio plain broken cashew kernels | €3.25 | 300 g | [dm Germany](https://www.dm.de/p/d/1694085/dmbio-cashewbruch) |
| Seeberger walnut kernels | €4.45 | 150 g | [dm Germany](https://www.dm.de/p/d/1004138/seeberger-walnusskerne) |
| LEBENSBAUM dried thyme leaves | €2.25 | 20 g | [dm Germany](https://www.dm.de/p/d/2032341/lebensbaum-thymian-gerebelt) |
| LEBENSBAUM dried oregano leaves | €1.95 | 15 g | [dm Germany](https://www.dm.de/p/d/1922952/lebensbaum-oregano-gerebelt) |
| dmBio dried pitted dates | €1.65 | 200 g | [dm Germany](https://www.dm.de/p/d/1447036/dmbio-trockenfruechte-datteln-entsteint) |
| dmBio spelt flour type 630 | €1.25 | 1000 g | [dm Germany](https://www.dm.de/p/d/1440266/dmbio-dinkelmehl-type-630) |
| dmBio ground almonds | €3.45 | 200 g | [dm Germany](https://www.dm.de/p/d/1601027/dmbio-mandeln-gemahlen) |
| dmBio capers in wine vinegar | €1.95 | 90 g | [dm Germany](https://www.dm.de/p/d/3095647/dmbio-kapern) |
| Leimer plain breadcrumbs | €1.39 | 400 g | [Knuspr](https://www.knuspr.de/7103-leimer-semmelbroesel) |
| Galbani Ricotta | €2.99 | 250 g | [Knuspr](https://www.knuspr.de/2172-galbani-ricotta-40-fitr) |
| Galbani Mascarpone | €4.39 | 250 g | [Knuspr](https://www.knuspr.de/16719-galbani-mascarpone-italienischer-frischkaese) |
| Galbani Gorgonzola Cremoso | €3.79 | 150 g | [Knuspr](https://www.knuspr.de/2178-galbani-gorgonzola-cremoso-48-fett-itr) |
| Fuchs chicken / poultry stock | €3.39 | 400 ml | [Knuspr](https://www.knuspr.de/4811-fuchs-gefluegel-fond) |
| Fuchs veal stock | €3.29 | 400 ml | [Knuspr](https://www.knuspr.de/92913-fuchs-kalbs-fond) |
| Fuchs beef stock | €3.39 | 400 ml | [Knuspr](https://www.knuspr.de/4807-fuchs-rinder-fond) |

## Validation and installation

The release includes focused offline-price tests, the prior screenshot recipe tests, a Chromium check of the active v88 bundle and retailer evidence links, and the installer's regression gates. Deployment simulation covers missing/truncated evidence, failed preflight, failed activation, restart failure and rollback. The installer verifies all 453 price observations, 69 portions and the density table before stopping Home Assistant and again after installation.

Run the pinned `tools/deploy_offline_runtime_v88.sh` as a standalone script. It backs up the integration, runs preflight checks inside the Home Assistant container, allows 120 seconds for Docker shutdown, and restores the previous integration if activation fails. This release has not been installed on the user's Home Assistant by this workspace.
