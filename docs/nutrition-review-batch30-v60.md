# Nutrition Batch 30: 100 explicit food/state reviews

Base: `06ab4a513eef1eb143448893ea0e909aa5c84b2a` (Batch 29 / PR #121).

Five source files, `036` and `036b` through `036e`, add **100** explicitly
assessed target-to-FDC bindings against **36** exact records in the retained
snapshot. This batch is intentionally smaller than 250: an intended batch size
is not evidence for a food substitution. All 221 earlier source files and all
12 holds remain unchanged. The selection is not the first 100 search results or
an automatic reuse of another target's accepted binding.

## Food identity and state

The batch covers raw vegetables and fruit, specified single spices, plain
butter, whole raw egg and plain water/ice. Examples preserve the distinction
between turnip greens and turnip root, raw burdock and boiled burdock, raw
shallot and fried shallot, coriander seed and coriander foliage, and raw
edible-podded peas and shelled green peas. Butter with unspecified salt status
uses `Butter, NFS`, not an invented salted/unsalted formulation.

These are **generic per-100-g ingredient estimates**, not brand-, cultivar- or
trim-specific laboratory measurements. Whole versus ground dry spices are used
only as generic references for the same spice; this supplies no spoon, seed or
stick weight. An infusion ingredient's binding does not establish that a removed
stick or stalk was consumed. Raw/peeled/cut descriptions do not establish an
edible yield, density or cooking conversion. No nutrient values were fetched,
populated or invented, and no runtime recipe calculations were changed.

Seventeen counterexamples remain explicitly unapproved by this batch, including
salt-and-pepper mixtures, mint with unspecified species, fresh tarragon versus a
dried reference, fresh sage versus a dried reference, microwaved pumpkin versus
raw pumpkin, soaked gelatin versus dry powder, and butter already mixed with
chocolate or flour. These are unresolved examples, not new holds on historical
reviews or a claim that every other candidate has been fully audited.

## Evidence receipts

The unchanged full candidate file has SHA-256:
`e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`.
The reference manifest remains:
`e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`.

Every new source uses the existing `retained-reference-record` contract. The
selected FDC record occurs in its own target-local candidate list for only one
of these targets; the other **99** refer to exact records retained elsewhere in
the same snapshot. Each receipt locates its source target, source rank and
canonical candidate hash. It is not the destination's rank and not permission
to copy a source identity or source decision. No held source target is used.
The existing loaders, strict historical checks and hold gates are unchanged.

## Resulting checkpoint

| Measure | Count |
| --- | ---: |
| Recorded target bindings | 4,481 |
| Recorded bindings not on hold (not a blanket certification) | 4,469 |
| Explicitly held targets | 12 |
| Never-recorded targets remaining | 1,838 |
| Remaining or held targets | 1,850 |
| Original provenance discrepancies still reported | 11 |
| Provenance discrepancies outside the hold set | 0 |
| Older targets outside retained-snapshot scope | 446 |

The full-file hold audit still returns **exit 2**, deliberately. Scoped unheld
manual inspection is allowed, but overall readiness and nutrition-complete
activation are not granted. The 100 added bindings are not 100 new populated
nutrient profiles and are not approval of all earlier bindings.

## Regression and full-file checks

The 14 Batch 30 tests lock all source files, all destination identities and
usage counts, every exact FDC receipt, the earlier 221-file fingerprint and
4,381-binding fingerprint, the 12-hold registry, loader propagation, duplicate
rejection, provenance drift failures, food-state decisions and 17 deferred
examples. The committed gzip fixture is clearly labeled a **projection**:
100 destination identity/usage projections and 32 source-row projections
containing 36 exact original candidate records, plus deferred examples. It is
not the original file and cannot independently prove that file's byte hash.

The downloadable bundle retains the original full evidence file and a full-file
audit. Source candidate records and destination projections are checked against
that file separately. CI now runs all nutrition-batch regression tests and
preserves the exact-head checkpoint and tracked source archive.

Use the existing project virtual environment for reproduction:

```sh
REPO="$HOME/project/cook4me/repo"
"$REPO/.venv/bin/python" -m unittest discover -s "$REPO/tests" \
  -p test_release_catalog_nutrition_review_batch30_v60.py -v
"$REPO/.venv/bin/python" "$REPO/tools/nutrition_review_holds_v60.py" \
  --evidence /path/to/saved/fdc-target-candidates-offline.v60.json \
  --output "$HOME/project/cook4me/logs/batch30-audit-$(date +%Y%m%d-%H%M%S)"
```

Do not regenerate the available evidence or edit old candidate ranks to force a
zero exit status. No provider/FDC crawl, release, live deployment, restart or
catalog activation is part of this batch. The next queue contains exactly
1,838 unchanged original rows, with the 12 held targets remaining separate.
