# Batch 34: 18 explicit salmon, ham and input-ingredient references

Continue from Batch 33 at `588ba93181a42254ce9e6c99917d92c609909fbe`.
One new source file (`040`) binds 18 full target IDs to nine explicitly selected
records from the unchanged retained evidence. These are generic reference
matches, not 18 populated nutrient profiles or laboratory/product certificates.

## Decisions and boundaries

Five salmon targets use **Fish, salmon, raw**. The generic record avoids choosing
an unstated species or wild/farmed origin. Unqualified salmon is reviewed as raw
recipe input, not as proof that every use of that ingredient is raw. The explicit
boning, skinning and cutting qualifiers stay in their original target names.
The 150 g steak label does not establish boneless edible mass, and the
sashimi-grade wording is not a food-safety certification. Salted/seasoned salmon,
smoked-fish alternatives, mixed-fish skewers and roe remain separate.

Two explicitly cooked-ham targets use **Ham**; two explicitly named
Parma-ham/prosciutto targets use **Ham, prosciutto**. These decisions do not turn
unspecified Italian ham or every cured ham into prosciutto. No exact brand,
protected origin, curing age, fat/salt formulation or slice weight is certified.

Four Cognac/Armagnac targets use the generic **Brandy** input reference. They are
not a liqueur blend, cocktail or measured finished sauce. The original names and
the `tbsp` qualifier remain intact; no alcohol strength, evaporation, retention,
density or tablespoon-to-gram conversion is supplied.

Fine bulgur for meatballs is reviewed as the separate **dry bulgur** input, not a
meatball or a soaked grain. **Wax beans** use raw yellow snap beans rather than
mature dried seeds or a cooked bean profile. **Boiled Savoy cabbage leaves** use
the cooked Savoy reference rather than raw cabbage; the generic cooked record
does not measure exact salt uptake, cooking time or drained moisture.

Almond dragees use the **sugar-coated almond** confectionery reference, not plain
almonds. Optional Tabasco drops use the retained ready-to-serve pepper sauce
record explicitly labeled **TABASCO**, not dried chili. Neither decision supplies
piece/drop weights, exact coating ratios, bottle variants or current formulation
certificates. Optional does not automatically mean zero consumption.

Twenty boundary examples remain unapproved by this batch, including seafood
parts/treatments, ham ambiguity, beverage mixtures, whole/shelled cardamom wording,
soaked freekeh and blanched/refreshed cabbage. They are not additional historical
holds, an exhaustive classification of the queue, or proof that no future
reference can resolve them. Prior deferral documents remain unchanged.

## Evidence and reproducibility

Full candidate-file SHA-256:
`e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`.
Frozen reference-manifest SHA-256:
`e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`.

Seventeen selected records are found outside their destination's original
candidate list; one is also destination-local. Receipts pin the actual source
target, source rank, candidate-record hash and full evidence hash. Source ranks
are not destination ranks. Locating a previously selected FDC record does not
copy the locator target's identity approval. No held target is a destination or
locator, and no search result was automatically accepted.

The compressed test fixture is explicitly a projection: nine source rows retain
nine exact original candidate records; 18 destination projections retain full
IDs, names, kinds and usage fields; 20 deferred identities retain their reasons.
The fixture is not the full evidence. Independent comparisons against the full
retained file verified all projections and the exact remaining-queue subtraction.

All 234 earlier source files / 4,604 earlier recorded bindings and the 12-hold
registry remain byte-for-byte unchanged. There are now 4,622 recorded targets,
4,610 recorded and unheld, 1,697 never-recorded targets and 1,709 remaining-or-held
targets. The 12 holds still cover 22 exact ingredient identities. Every remaining
row is unchanged and in its original order.

The 11 historical provenance discrepancies remain visible, with zero outside the
hold set. The 446 earlier recorded targets outside the retained snapshot remain
outside its verification scope. Recorded counts do not certify all earlier
mappings. Audit exit 2 and global readiness false remain intentional: permission
to inspect the unheld queue is not approval of nutrition completion or activation.

## Tests and local instructions

Twenty new tests cover source bytes, prior file/binding fingerprints, complete
ID disjointness, holds, all receipts, loader propagation, duplicate/drift failures,
food-state boundaries and deferred examples. All 878 Python tests pass locally;
version, JSON and Python compilation checks pass. Local full-suite temporary
storage is memory-backed because of the previously observed sandbox SQLite
storage issue. No application/test workaround or workflow change is introduced.
GitHub source/frontend/HACS and checkpoint validation are required before merge.

From the source checkout, using its project virtual environment:

```sh
.venv/bin/python -m unittest discover -s tests -p '*nutrition_review_batch34*' -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/nutrition_review_holds_v60.py \
  --evidence /path/to/saved/fdc-target-candidates-offline.v60.json \
  --output /path/to/new/project-local/logs/batch34-audit
```

The audit requires a new output directory and intentionally returns 2 while
holds remain. No device, Home Assistant connection, provider credentials or
network access is needed for these offline checks. Tests do not install or
activate the catalog. No provider/FDC crawl, historical-rank rewrite, hold
removal, runtime/workflow change, release, deployment, restart or live cache
mutation is part of this batch.
