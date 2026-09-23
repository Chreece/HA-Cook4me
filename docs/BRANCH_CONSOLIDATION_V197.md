# Cook4Me branch consolidation — v197

## Scope

The user requested merging outstanding work and retaining only `main`.
PR #238 (manual barcode search, outside Save/Discard, guided focus) was merged
as `0a6f8cd73b23debcb2585e1e75cd745110188453` before the audit.
The read-only audit at `5223eb462d1e41d51fc1e05b086e810a6ace3e7d` found
287 branches, including main. The per-branch SHA, PR history and conflict
resolution are recorded in `BRANCH_CONSOLIDATION_V197.json`.

172 heads were ancestors, 46 were exact heads of merged PRs, one was
patch-equivalent, and one already produced the main tree. Of 66 remaining
heads, 44 contained only file versions already current or historical in main;
22 needed explicit review. Every original head is retained in consolidated
commit ancestry, including superseded experiments. No destructive history
rewrite or tag/release deletion is required.

## Integrated outstanding work

- v196 manual editor from PR #238, preserving the existing scanner, receipt and
  Greek audit features v191–v195.
- Previously local pricing patches v189/v190: explicit Greek measurement
  normalization, safer cost caching and initialization, mapped ingredient
  identities, supermarket-language labels independent of country/currency,
  local observation boundaries and missing-data reporting.
- The unmerged post-activation nutrition continuation: exact-ID source records,
  supplemental official-composition evidence, reviewed eligibility and hold
  handling. Provider references remain generic estimates, not exact product
  analyses. No internet data or new inferred nutrient values were fetched.
- The final semantic-review lane, reconciled against that newer nutrition
  snapshot. Recipe quantities/instructions, 16,952 recipes, 32,163 variants and
  all 11,748 ingredient IDs are unchanged. Source-local aliases retain their
  original IDs; reviewed equivalence does not authorize arbitrary substitutions.

The final catalog has 10,640 nutrient profiles, versus 9,354 before consolidation
(net +1,286). The nutrition-only branch had 10,770, but combined semantic safety
rules exclude 130 unconfirmed/ineligible bindings. Their source evidence remains
in history. Completing a semantic disposition does NOT make ambiguous foods safe
for nutrition, dietary or allergen filtering. The validator intentionally still
reports incomplete ingredient intelligence; runtime remains fail-closed.

## Conflict resolutions

Old v13 pantry data paths and alternative v59/v60 catalog/scale routes are
superseded by the active implementation. Older Greek overlays cannot overwrite
newer curated labels, and old build/version edits cannot roll the panel back.
The early guinea-fowl meat-and-skin proposal conflicts with the later explicitly
reviewed meat-only binding in `targets_095`; the later binding is retained.
Intermediate discovery/title-probe data remain accessible through ancestry.
Old temporary self-writing/export workflows are NOT reactivated.

`tools/reconcile_catalog_reviews_v197.py` performs an offline deterministic
reconciliation, checks exact source IDs, regenerates indexes through existing
builders, and rejects changes to recipes, ingredient IDs or retained exact-ID
nutrient values. `CATALOG_RECONCILIATION_V197.json` records its result.

## Reproducible reconstruction

The GitHub reconstruction gate exposed nondeterministic ties between aliases
that differ only in case. Semantic alias sorting now uses the original spelling
as a tie-breaker, and the reconciler emits canonical JSON object-key order.
Separate builds with Python hash seeds 1 and 42 must agree byte-for-byte;
reviewed source hashes remain mandatory before publication. Recipe and nutrition
values are unchanged by this reproducibility correction.

## Validation and cleanup

Before publication, the existing Validate command block and Greek, scanner,
receipt and manual-editor suites passed against the complete checkout and
combined catalog. Both recovered pricing suites passed (41 tests each), as did
semantic, nutrition eligibility, supplemental-evidence and hold regressions.
The full catalog validator passed with the expected incomplete-intelligence
warning. GitHub checks on the consolidation PR are the publication gate.

Deletion must verify every recorded branch tip is an ancestor of the final main
and still has its audited SHA. Changed/new branches are not silently deleted.
The original all-branch Git bundle is retained in GitHub Actions backup run
35853194745, artifact 10746870064 (30-day retention), and provided with the audit.
Full history also remains reachable from consolidated main, so artifact expiry
will not remove it. Cleanup logs record the actual result.

Repository consolidation only: no live Home Assistant deployment, real-camera
or external price/barcode/AI-provider test was performed. Nothing in this change
restarts Home Assistant or modifies the user's inventory/configuration.
