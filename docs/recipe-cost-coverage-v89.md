# v89: screenshot ingredient gaps

Audit date: 2026-09-16. Market: Germany / EUR. Baseline: `38c044f5619af3c68dabaec92d2b0b2e61849a79` (v88).

Eleven new named German retail observations bring the offline snapshot to **464 observations** (371 Open Prices, 92 retail, one regional water tariff). Seventeen USDA portions and two published reference portions add fruit counts, nut spoon weights, syrup conversions, curry paste and whole shallots. All quantities are disclosed estimates; original cooking and nutrition data are unchanged.

The Czech pasta family has one reviewed costing correction: its liquid tofu row means tofu cream in the original Tefal recipe. It uses a separate pricing identity, so solid tofu inventory and prices cannot be used for cream. Only the three serving variants of this family are affected.

## Screenshot results

Counts are ingredients priced; complete means all listed ingredients have an estimate, not that prices are exact household purchase costs. The strawberry-coconut representative has 3/10 baseline coverage here; the screenshot shows 2/10, which can differ with serving variant or prior runtime/evidence state.

| Recipe | v88 | v89 | Still unresolved |
|---|---:|---:|---|
| Curry de tofu et brocolis | 4/6 | 5/6 | Salt |
| Gachas de muhlama | 4/5 | 5/5 | None |
| Gesundes Porridge | 3/7 | 6/7 | Chocolate |
| Mushroom risotto | 4/6 | 5/6 | Chestnut |
| Pear and honey couscous | 2/5 | 4/5 | Cinnamon |
| Porridge chocolat noisettes | 1/5 | 5/5 | None |
| Porridge fraises coco | 3/10 | 8/10 | Salt, Chia seed |
| Porridge fruits sirop d'érable | 4/7 | 6/7 | Coconut |
| Prunes in muesli crumble | 5/7 | 7/7 | None |
| Risotto alla milanese | 2/8 | 3/8 | Stock, Saffron, Bone marrow, Parmesan, Salt |
| Risotto aux champignons | 5/8 | 7/8 | Salt |
| Schoko-Porridge mit Mandeln | 4/8 | 7/8 | Speculoos biscuits |
| Směs těstovin s uzeným tofu | 4/7 | 5/7 | Bean, Salt |
| Къри със зеленчуци | 5/7 | 5/7 | Radish, Salt |

## Whole catalog

32,163 language/serving variants, not distinct recipe families. Food ingredient occurrences priced rise from **103,647 to 106,862 (+3,215)**; water coverage is unchanged. Complete variants rise from **3,559 to 3,686 (+127)**. Variants with no cost fall from **1,990 to 1,944**. German variants gain 357 priced food occurrences.

Unknown amounts remain unknown: unspecified salt, chia, cinnamon and parmesan; ambiguous chocolate pieces, saffron packets and bone marrow quantities. Radishes still lack a verified German price with a usable mass/count basis. The mushroom risotto provider labels an ingredient Chestnut; it is not globally reclassified as a mushroom without source confirmation. Generic stock and beans remain ambiguous.

## Evidence and assumptions

Every price record includes its original retailer URL, named product, package basis, date and country. Regular prices exclude membership/promotion discounts. Almonds may use a whole-kernel price reference with form-specific sliced/slivered spoon weights. Generic oats use a rolled-oat reference. Generic dates use the named dried pitted date reference. Arborio and generic risotto rice use the named Carnaroli benchmark; none are asserted to be a national average. Fresh coconut uses a whole-coconut price plus the USDA edible-meat yield, with both spoon and yield portions disclosed; it is never a dried-coconut price.

- [Thai Kitchen manufacturer: 1 tablespoon red curry paste is 15 g](https://www.clubhouseforchefs.ca/en-ca/products/thai-kitchen/thai-kitchen-red-curry-paste). Other brands may differ.
- [Alnatura recipe: one shallot is 30 g](https://www.alnatura.de/de-de/rezepte/suche/crispy-chilioel-106501/). A published recipe reference, not a universal bulb size.
- [Tefal Czech tofu cream identity](https://www.tefal.cz/recepty/detail/index/source/PRO/id/287823/) and [two-serving version](https://www.tefal.cz/recepty/detail/index/source/PRO/id/287825/).

## Verification

The real offline costing tests exercise all 34 serving variants belonging to the 14 selected screenshot recipes; network lookups fail the test. Tests also cover source attribution, country boundaries, native purchase priority (existing regression), distinct tofu/cream identities, missing amounts and fresh/dried form separation. The browser test checks quantity-source links and rejects deceptive domains. The installer validates all five evidence files before stopping Home Assistant and again after activation, with backup and rollback retained.

Reproduce: `python tools/audit_recipe_price_coverage_v89.py --as-of 2026-09-16 --output docs/recipe-cost-coverage-v89.json`.
