# Nutrition Batch 29: 250 explicit retained-reference reviews

Base: PR #120, commit `6e18fcf598c0cb774d69fd336207bd59b04e588c`.

## What was reviewed

Thirteen source files (`035`, `035b` through `035m`) add 250 independently named
and ID-bound decisions against 38 exact FDC reference records. They cover raw
produce, fresh herb foliage, eggs and plain ingredients with defensible food
identity/form matches. Each target keeps its original full ID, kind, canonical
English name and usage count, with a food/state-specific rationale.

These are **generic per-100-g ingredient estimates**, not exact cultivar, brand
or trimmed-portion laboratory values. An ingredient's cutting, washing, peeling,
grating or intended-use text is retained. Piece counts, cut dimensions and spoon
sizes do not establish edible mass or authorize a density conversion. Egg-size
text does not establish shell-free mass. No new nutrient values were fetched,
invented, calculated, installed or declared complete by this batch.

## Why reference receipts were needed

The frozen target-local top-eight retrieval is incomplete. Examples include
`Ground cumin` returning ground meats and `Potato starch` returning flour/bread.
Neither is approved by substituting those candidates. There are 7,410 unique FDC
description records elsewhere in the **same retained snapshot**, with no
conflicting metadata for a repeated FDC ID. This is a partial description corpus,
not the full USDA reference dataset and not a source of nutrient values.

After explicit food/state review, this batch uses exact FDC records found in that
retained corpus. Only one of these 250 selections was also present in its own
original top-eight list. The other 249 were **not** accepted from an invented or
silently rewritten target-local search. Each new source file states
`evidenceBindingScope=retained-reference-record` and pins the actual evidence
file SHA-256. Its FDC-keyed receipts identify the original source target, original
source candidate rank, and SHA-256 of the canonical JSON candidate record.

The source target is an evidence locator, **not** a copied provider identity,
semantic concept, accepted historical binding or source of approval. Each
destination was assessed separately. No held source target is used. The original
snapshot, all 208 earlier source files and all 12 hold records remain unchanged.

A source candidate rank is stored as `sourceEvidenceCandidateRank` and never as
`candidateEvidenceRank`: it is not the destination's retrieval rank. The audit
checks destination ID/name/kind and reference/catalog first, then validates the
explicit source receipt. Ordinary historical reviews retain their original
strict target-local checks; they gain no implicit cross-target fallback.

The checkpoint and normal review loader retain these receipts; generated target
profiles carry them forward as provenance. Neither helper chooses a candidate
or treats matching metadata as semantic identity proof.

## Verified state after the batch

| Measure | Count |
| --- | ---: |
| Recorded targets | 4,381 |
| Explicitly held targets | 12 |
| Unheld recorded targets (not a full semantic certification) | 4,369 |
| Never-recorded targets remaining in the retained snapshot | 1,938 |
| Unresolved-or-held targets | 1,950 |
| Original provenance discrepancies, preserved | 11 |
| Discrepancies outside the hold set | 0 |
| Earlier recorded targets outside this snapshot's scope | 446 |

The full evidence file is pinned to
`e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`.
The frozen reference-manifest SHA-256 remains
`e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`.

The scoped unheld-review gate can remain true while overall readiness remains
false. The 12 holds are not lifted, the remaining queue is not complete, and
these 250 decisions are not 250 newly populated nutrient profiles.

## Verification and reproduction

The 18 Batch 29 regression tests cover all IDs, source-file digests, held-target
exclusion, explicit manual-review policy, source-rank semantics, exact reference
receipts, destination identity, legacy non-fallback, drift failures and receipt
propagation to generated profiles. The compressed committed fixture is explicitly
a **projection**: 35 exact original source rows and 250 destination identity/usage
projections. CI tests that locked projection; it does not pretend to independently
re-hash the entire original snapshot. The downloadable work bundle retains the
full snapshot for end-to-end reproduction.

Run the full-file audit on the existing saved evidence using the project virtual
environment (no provider or FDC crawl):

```sh
REPO="$HOME/project/cook4me/repo"
"$REPO/.venv/bin/python" "$REPO/tools/nutrition_review_holds_v60.py" \
  --evidence /path/to/existing/fdc-target-candidates-offline.v60.json \
  --output "$HOME/project/cook4me/logs/batch29-audit-$(date +%Y%m%d-%H%M%S)"
```

Exit **2 remains expected**, because holds remain unresolved. Output goes to a
new directory, and only the compact summary is printed. Do not reconstruct
existing captures or edit historical ranks to obtain a green completion flag.

No runtime deployment, Home Assistant restart, catalog activation or release is
part of this batch. Next is a separately reviewed Batch 30 from the retained
1,938-target queue; compounds, missing food identities and held targets must not
be filled with approximate substitutes just to meet a batch size.
