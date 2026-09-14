# Batch 31: explicit preparation-state nutrition references

This batch adds **62** independently assessed target-to-FDC reference bindings
in four new files (`037`, `037b`, `037c`, `037d`; 20/20/20/2 items). It continues
from Batch 30 at `d8a2b2480dcc1270082362814720aa108fe55aca`.

## Reviewed decisions

The 26 selected retained FDC records distinguish dry pasta (10 targets), fresh
unfilled as-purchased pasta (4), and cooked pasta (3). Whole-wheat pasta with no
preparation state and stuffed pasta with unknown filling remain deferred.
Raw shrimp (3) and explicitly cooked frozen shrimp (2) use different profiles.
Drained canned sweetcorn is not mapped to solids plus liquid, and unprepared
frozen sweetcorn is not mapped to boiled corn. Plain and toasted baguette,
dry coffee and drinks, and white/lower leek portions retain their distinctions.

The generic almond/pistachio records explicitly say not further specified; the
labels do not prove salt or roasting status. Unspecified-color pepper vegetables
use the raw not-further-specified pepper record, not an invented color or a
peppercorn-spice profile. Other selected references cover raw produce, phyllo
dough, Fontina, plain cola, dehydrated onion/garlic and standalone baking soda.
All 62 exact identities, selected FDC IDs and explanations are in the source files.

These are **generic per-100-g edible-ingredient references**, not exact cultivar,
brand, product fortification, sodium formulation, measured moisture or laboratory
nutrition. The fresh pasta reference is not proof of exact egg content. The corn
references are generic yellow sweetcorn, not a declaration of kernel color in
the provider identity. No shell/core/skin yield, sheet weight, draining factor,
fresh/dry conversion, cooking yield or volume-to-mass conversion is supplied.
A separate estimate still needs an evidence-supported edible mass in the proper
state. No nutrient values are fetched or populated by this batch.

## Explicitly unapproved examples

The fixture preserves 18 boundary examples, including soaked rice and gelatin,
dried breadcrumbs, fresh tarragon, unspecified coconut, starch slurry, isolated
wheat starch, mint species, alternative biscuits, tuna with unknown packing
medium, flour plus bicarbonate, stuffed pasta, pasta cooking water, a branded
soy/wheat product and feta marinade. They stay in the unreviewed queue. They are
**not** additional historical holds, and this is not an exhaustive classification
or rejection of the remaining queue.

## Evidence, invariants and counts

The unchanged full candidate file is pinned by SHA-256
`e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`.
The frozen reference manifest remains
`e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`.

All selections use the existing `retained-reference-record` receipts. The source
rank locates an exact saved record; it is not a destination search rank or
permission to copy another target's identity/decision. Six selections also occur
in the destination's original top-eight list; 56 use a retained record elsewhere
in the same full snapshot. None is automatically selected by rank or lexical
matching. Held targets are neither destinations nor reference locators.

All **226** earlier review files / **4,481** recorded IDs and the **12**-hold
registry remain unchanged. After this batch there are **4,543 recorded IDs**,
**4,531 unheld recorded IDs**, **1,776 never-recorded candidates**, and **1,788
remaining-or-held targets**. Historical review counts are not blanket semantic
certification. The 446 older targets absent from the retained snapshot remain
outside its verification scope. The original 11 provenance discrepancies stay
visible inside the unchanged hold set; they are not rewritten or hidden.
The audit is expected to exit 2 while holds remain, not authorize activation.

## Reproduction and tests

The compressed CI fixture is explicitly a **projection**, not the full snapshot.
It contains 24 source-row projections with 26 exact original candidate records,
62 destination identity/usage projections, and the 18 deferred examples. Full
byte-pinned evidence and the untouched next queue are retained in the batch bundle.

Run from the repository using its maintenance Python environment:

```sh
python -m unittest discover -s tests -p '*nutrition_review_batch31*' -v
python -m unittest discover -s tests -v
python tools/nutrition_review_holds_v60.py \
  --evidence /path/to/existing/fdc-target-candidates-offline.v60.json \
  --output /path/to/new/project-local/logs/batch31-audit
```

The tests verify exact IDs, prior-file hashes, receipts, hold integrity,
food-state distinctions and deferred counterexamples. Tests do not provide a
laboratory validation of generic nutrition estimates. The existing checkpoint
workflow discovers this batch's tests automatically; no runtime or workflow code
changes are needed. No provider/FDC crawl, release, catalog activation, live
Home Assistant deployment, restart or installed-cache mutation is part of this work.
