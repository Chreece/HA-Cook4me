# Batch 33: 29 explicit generic ingredient references

Continue from Batch 32 at `adc5b171b45f4650c8afafa0eb8b10e23ac24b48`.
Two new source files (`039`, `039b`; 20/9 items) bind 29 full target IDs to
15 explicitly selected records in the unchanged retained evidence. There is
no acceptance quota, new provider/FDC request or historical review rewrite.

## Decisions and boundaries

Four minced-meat targets distinguish raw beef from raw pork. The selected
generic raw records do not impose an unstated lean/fat percentage, cooked
state, mixed-meat composition or meatball formulation.

Nine unbranded vegetarian-sausage targets use the retained generic **Sausage,
meatless** record, never pork sausage or plain tofu. Cutting only does not add
a frying step. This is a category-level nutrition estimate: it is not a claim
about a product's protein source, fat/salt formulation, vegan status, allergens
or certification. Branded HERTA sausage and non-sausage strips remain deferred.

Four sake targets bind only the separately measured input beverage used in a
later sauce/seasoning step. They do not bind a completed marinade, substitute
mirin or sake lees, or establish alcohol concentration/retention, salt addition,
evaporation, density or a volume-to-mass conversion.

Almond drink uses the explicitly unspecified almond-milk record; sweetening,
flavor and fortification are not invented. Crushed cornflakes use plain cereal
without milk. Squid and cuttlefish, sea bass and trout retain separate generic
raw edible-ingredient records. Cleaning/cutting-only and unqualified fish inputs
are reviewed at the raw input stage, not asserted to be measured finished-food
profiles. The records do not certify an exact species, age, discarded-part yield,
raw-to-cooked conversion or whole-animal/fillet weight. Smoked trout, ink and
salt-water-thawed squid are not accepted by these mappings.

Fresh basil remains fresh rather than dried. Fresh chili of unspecified color
uses raw hot pepper without a color assumption; the explicitly red chili uses
a separate raw red-hot-chili record. Raw pork backfat is not rendered lard or
salted pork; whole pork shoulder retains lean and fat rather than a lean-only
or specific-subcut assumption.

Twenty explicit boundary examples remain unapproved by this batch. They cover
brands and product classes, mixed/unknown meat, meatballs, pork collar and cured
pork, treated seafood, sake lees/mirin, dairy/plant alternatives, unidentified
plant drinks, peeled potatoes, mint variety, seasoning mixtures and soaked
gelatin. They are not new historical holds or an exhaustive classification of
the remaining queue. Prior deferral records remain unchanged.

## Evidence and reproducibility

Full retained candidate SHA-256:
`e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`.
Frozen reference manifest SHA-256:
`e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`.

All 29 choices locate their selected reference elsewhere in this same retained
file; none is falsely labeled a destination-local result. Existing receipts
pin the actual source target, rank, complete candidate-record hash and full
source-file hash. A locator is not another target's identity approval and does
not authorize automatic rank-based acceptance. No held target is a destination
or reference locator.

The compressed fixture is explicitly a projection: 15 source-row projections
with 15 exact original candidate records, 29 destination identity/usage
projections, and 20 deferred identities/reasons. Independent full-file checks
verify every projection against the original snapshot. The whole file is
retained in the user bundle, not misrepresented by the small CI fixture.

## Invariants and counts

All 232 earlier source files / 4,575 recorded bindings and the 12-hold registry
are byte-for-byte unchanged. There are now 4,604 recorded targets, 4,592
recorded and unheld, 1,715 never-recorded candidates and 1,727 remaining-or-held
targets. Twelve holds still cover 22 exact ingredient identities.

The next queue is exactly the old 1,744 rows minus the 29 newly reviewed IDs;
all remaining contents and ordering are preserved. Eleven historic provenance
discrepancies remain visible, with zero outside the hold set. The 446 earlier
targets outside the retained snapshot remain outside its verification scope.
Recorded totals do not certify every historic mapping. Audit exit 2 and global
readiness false remain intentional: unheld-queue inspection is not completion
or catalog-activation approval.

## Validation and scope

Twenty new regression tests cover immutable bytes and earlier file/binding
fingerprints, full-ID disjointness, all receipts, loader propagation, hold
integrity, candidate drift, duplicates, preparation boundaries and deferred
examples. All 858 Python tests pass locally. The local full suite uses
memory-backed temporary storage because the prior sandbox had SQLite overlay
I/O errors; no application/test workaround or workflow change is introduced.
GitHub source/frontend/HACS and checkpoint validation are required before merge.

Use the project virtual environment for local checks:

```sh
.venv/bin/python -m unittest discover -s tests -p '*nutrition_review_batch33*' -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/nutrition_review_holds_v60.py \
  --evidence /path/to/saved/fdc-target-candidates-offline.v60.json \
  --output /path/to/new/project-local/logs/batch33-audit
```

These are reference bindings, not 29 populated nutrient profiles. Confidence
refers to the generic reference match, not laboratory or exact-product accuracy.
No density, piece weight, edible yield or cooking factor is added. There is no
provider/FDC crawl, hold removal, runtime/workflow change, release, catalog
activation, deployment, restart or live Home Assistant/cache mutation.
