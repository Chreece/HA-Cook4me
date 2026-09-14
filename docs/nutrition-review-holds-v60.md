# Targeted nutrition re-review and enforceable holds

This change addresses the findings saved with checkpoint PR #119. It makes no
replacement FDC selections and preserves all 208 historical review files, all
4,131 recorded target IDs, and the original 11 candidate-provenance discrepancies.
Those historic records remain available for audit and duplicate-ID detection;
recorded does not mean currently permitted for nutrition resolution.

## Scope and decisions

Twelve exact targets are on hold. Two have explicit food-form/composition
mismatches: chicken stock **powder** was bound to home-prepared stock, and a
mustard **plus creme fraiche** mixture was bound to mustard alone. No replacement
is defensible from the retained target candidates without further evidence.

The other ten holds are not assertions that every food binding is wrong. They
require evidence reconciliation and/or clarification of preparation, formulation,
or specific product identity:

| Target name | Reason for hold |
| --- | --- |
| Almond puree | Recorded FDC 2262074 absent from the retained target candidates |
| Montbeliard sausage / sausages (two exact targets) | Specific sausage versus generic pork sausage; rank discrepancy |
| Consomme stock cube | Selected record specifies chicken; broth type not established |
| Coriander puree | Puree composition not established by the raw-leaf record |
| Pumpkin puree | Raw state of puree not established |
| Bouillon cube; consomme granules (two exact targets) | Selected low-sodium formulation not established |
| Nestle dark dessert chocolate | Branded formulation not established by generic candy record |
| Sesame puree | Rank-only provenance discrepancy; no food mismatch asserted |

The registry contains each full target ID, original FDC ID/description/type/rank,
original source filename and byte SHA-256, observed rank in the retained snapshot,
reason, and the exact member ingredient IDs from the existing semantic compiler.
It is an explicit negative decision, not a name/rank-based automatic classifier.

The source compiler proves 21 source-local member IDs across 11 held concepts.
The remaining hold is the single provider identity `M_FOOD_447`: **22 ingredient
identities total**. New aliases of an already-held concept are also blocked.
Provider identities are never grouped by name and the same FDC ID remains usable
for an unrelated, separately reviewed food.

## Enforced paths

`nutrition_review_holds_v60.py` validates the registry against the current full
review corpus and semantic memberships. Missing/corrupt holds, duplicate holds,
source-byte or binding drift, and unsupported approval statuses fail closed.
Its index is immutable for one maintenance process; restart a process after a
review/registry change rather than changing its inputs underneath it.

Both exact-ingredient and compact-target resolvers check holds **before** cache
acceptance and before fetching FDC food details. Held entries become explicit
pending tasks. Returned caches exclude held profiles, including held entries
outside the current queue. Input dictionaries and historical review files are
not modified by resolution.

The shared reviewed-profile predicate rejects held targets and their proven
member IDs even if old profiles have no target metadata. The existing queue and
finalizer therefore cannot reuse their cached or embedded nutrition. Finalization
rebuilds recipe vectors and retains incomplete nutrition coverage rather than
counting a held food as resolved. An independent catalog-validator check rejects
held nutrition even in incomplete maintenance validation. Holds also cannot be
used as precedent in the exact-canonical reuse proposal tool.

This protects maintenance resolution/finalization/validation. It does not claim
to remotely erase an old local cache or an already-installed catalog. Nothing is
deployed to Home Assistant and the bootstrap catalog remains inactive.

## Reproducing the retained-evidence audit

Run with the existing project virtual environment, from the repository:

```sh
"$HOME/project/cook4me/repo/.venv/bin/python" \
  tools/nutrition_review_holds_v60.py \
  --evidence /path/to/retained/fdc-target-candidates-offline.v60.json \
  --output "$HOME/project/cook4me/logs/nutrition-hold-audit-$(date +%Y%m%d-%H%M%S)"
```

The output directory must be new. Exit **2 is expected while holds exist**; it
writes `hold-audit.json` and `summary.json`, prints only the summary, and does not
modify the saved evidence, source reviews, or catalogs. No network is used.

Full candidate-file SHA-256:
`e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`.
Reference-manifest SHA-256:
`e135d4235a897688e37f8561602820bb84d186e91c09d9f654f52bf0d8fab29d`.

The compressed committed test fixture is an explicitly labeled 12-target subset of the
retained evidence, not a replacement for that full 5,873-target snapshot.

## Counts and separate gates

At the PR #119 baseline:

- **4,131 recorded** targets, including **12 held**; **4,119 unheld recorded**
  targets have not been independently certified by this targeted audit.
- **2,188 never-recorded** targets remain in the retained snapshot.
- **2,200 unresolved-or-held** targets: 2,188 plus the 12 explicit holds.
- All **11 raw provenance discrepancies remain visible**, with zero discrepancies
  outside the explicit hold set. The 446 earlier recorded targets outside the
  available snapshot remain explicitly outside its provenance-check scope.

`readyForManualReview` retains the original checkpoint result (false for this
snapshot). `readyForUnheldManualReview=true` means the disjoint, unheld candidate
queue can be inspected without using held bindings as precedent. It neither
approves any candidate nor authorizes catalog activation. An unexplained
provenance discrepancy outside the hold set makes that scoped gate false.

Lifting a hold requires a separate explicit, evidence-backed re-review with
matching target identity, food state/composition, exact FDC evidence and tests.
Do not change historical ranks just to make the audit green. Never fill a batch
quota with approximate substitutes.
