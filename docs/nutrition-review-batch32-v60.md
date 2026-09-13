# Batch 32: 32 explicit retained-reference decisions

This batch continues from Batch 31 at
`9108847875aff62d0d6a7da2d89b36cc31eeb49e`. It adds **32** target-to-FDC
reference bindings in two new files (`038`, `038b`; 20/12 items), using **21**
explicitly selected records in the already-retained evidence. It does not set
an acceptance quota or infer that every remaining food has a defensible match.

## Decisions and boundaries

Liquid cream without a percentage uses the retained record explicitly
unspecified as to light, heavy or half-and-half. Milk powder uses dry,
not-reconstituted milk; full-fat milk uses whole milk. Temperature-only handling
of unspecified liquid milk does not establish a fat percentage or evaporated
milk concentration. These generic records preserve uncertainty rather than
claiming exact product fat, fortification or density.

The earlier **Dried breadcrumbs** deferral is now resolved by an actual retained
**dry, grated, plain breadcrumb** record (FDC 174928), not by a fresh-to-dry
conversion from soft white bread. The old deferral and review files remain
unchanged. Three explicitly crumbled/grated white-bread targets use the retained
record that includes **soft bread crumbs** (174924). White breadcrumbs with no
fresh/dried state, unspecified breadcrumbs and panko remain unapproved here.
French bread pieces are neither toasted bread nor dry crumbs.

Other decisions cover ladyfinger biscuits, shortbread, gummy confectionery,
unqualified wholemeal wheat flour, three single spices, raw edible bitter-melon
pods, as-supplied frozen edamame, steamed eggplant, raw grapefruit of unspecified
color, whole salad onions, plain unspecified vegetable oil for a future cooking
step, and raw veal liver with cutting only. Each full destination ID, exact FDC
ID, source receipt and semantic rationale is stored in the new source files.
Gummy shape/flavor does not establish fruit content, gelatin source, vegetarian
status, brand or sugar-free composition. Ground anise is not star anise.

**18 boundary examples remain unapproved** in the current fixture: numerical
cream/milk fat categories, numbered flour grades, wheat starch, unspecified
crumb moisture, panko, ladyfinger-or-wafer alternatives, soaked gelatin,
Savoy-cabbage drainage/salt basis, stalk-only salad onion, dairy-or-plant milk,
oil/yogurt handling, unspecified poultry liver, ground fenugreek, paprika paste
and coffee extract concentration. These examples are not additional historical
holds or an exhaustive classification of the remaining queue.

## Evidence and reproducibility

The full original evidence SHA-256 remains
`e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`.
The frozen reference manifest remains
`e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`.

All bindings use the existing retained-reference receipt contract. One selected
record also occurs in its destination's original top-eight list; 31 selections
use a record located elsewhere in the same file. The source ID/rank is a
locator for an exact record, not destination identity evidence, a fabricated
destination rank, automatic search-result acceptance or permission to copy
another target's historical decision. Held targets are neither destinations
nor source locators.

The compressed fixture is explicitly a **projection**, not the whole snapshot.
It contains 20 source-row projections with 21 exact original candidate records,
32 destination identity/usage projections, and 18 deferred identities/reasons.
The complete unchanged candidate file, all selected decisions and the exact
remaining queue are retained in the batch bundle for a separate full-file audit.

## Invariants and counts

All **230 earlier review files / 4,543 earlier recorded target IDs** and the
**12-hold registry** remain byte-for-byte unchanged. This batch gives **4,575
recorded targets**, **4,563 recorded and unheld**, **1,744 never-recorded
candidates**, and **1,756 remaining-or-held targets**. Twelve holds cover 22
exact ingredient identities. None is lifted by this batch.

The original 11 provenance discrepancies remain visible inside the hold set,
with zero outside it. The 446 earlier recorded targets outside the retained
snapshot remain outside its verification scope. Recorded totals are not a
blanket semantic certification. The hold audit deliberately exits 2 and keeps
global readiness false; unheld-queue inspection does not authorize activation.

## Tests and scope

Twenty new regression tests lock source bytes, complete prior file/binding
fingerprints, full destination IDs, exact source receipts, loader propagation,
unchanged holds, duplicate/drift rejection, food-state distinctions and deferred
boundaries. The existing nutrition-checkpoint workflow discovers the new tests
without a workflow or runtime-code change. Use the project's virtual environment:

```sh
.venv/bin/python -m unittest discover -s tests -p '*nutrition_review_batch32*' -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/nutrition_review_holds_v60.py \
  --evidence /path/to/saved/fdc-target-candidates-offline.v60.json \
  --output /path/to/new/project-local/logs/batch32-audit
```

These are **reference bindings, not populated nutrient profiles**. Confidence
refers to the reviewed generic reference match, not laboratory accuracy, exact
product formulation or measured moisture. There is no inferred density, piece
weight, edible yield, draining factor, oil absorption, or cooking/drying
conversion. No provider/FDC crawl, historical-rank rewrite, hold removal,
catalog activation, release, deployment, restart or live Home Assistant/cache
change is part of this batch.
