# Empty weekly generation: progress and executor audit — v200

## Reproduced causes

The v199 weekly generator emitted `catalog_index: 0/1` and then called
`search_filtered` WITHOUT its progress callback. The shared catalog search
already provided actual materialization/ranking/nutrition counters, but none of
those counters reached the weekly job. The first visible update could therefore
arrive only after the entire catalog/filter pass finished.

The old ETA layer could reuse a three-second historical duration for the 0/1
placeholder indefinitely. Whole-job duration history also mixed different
amounts of work and stage counters. That was not a reliable remaining-time claim.

Separately, the shared nutrient filter copied both entire saved nutrition maps
for every recipe. Those read-only inputs are now copied once per filter pass;
weekly candidate nutrition snapshots them once per bounded 30-row batch.
No recipe limit, filter, food identity, nutrient value or selection score is
changed by this optimization.

## Changes

- Forward the existing real progress callback through empty-week catalog search
  and filtering. Preparation with an unknown count is indeterminate, not 0/1.
- Run the catalog readiness check in HA's executor, including a cold cache.
- Marshal worker updates to the originating event loop and bound ordinary
  notifications to four per second. Stage boundaries and final counts remain
  visible; cancellation is checked even when a notification is suppressed.
- Cooperative cancellation stops read-only catalog and scoring work at the next
  checkpoint. The awaiting task drains its worker before releasing the existing
  weekly mutation lock, including repeated cancellation. It never publishes a
  partial plan or starts an overlapping worker via an early lock release.
- Show the current stage, measured stage count, and elapsed time in the job card.
  Update elapsed time locally once a second without polling HA or inventing work.
- Never use historical whole-job ETA for weekly generation. Show an estimate for
  the CURRENT STAGE only after at least two measured, advancing samples span a
  second. Reset rates at stage/denominator changes or counter resets.
- When no completed work has been reported for 15 seconds, remove the estimate
  and show that interval explicitly. This does not assert that the backend has
  crashed, that work finished, or that the server is still reachable.
- Keep cancellation, errors, account/entry scope, concurrent job ownership and
  timer cleanup. Other job types retain their existing presentation.
- Runtime URL/element is rotated to v200. v199 filters/recipe-close/receipt
  placement, v198 stock coverage, and manual Save/Discard remain composed.

## Validation and limits

Local production-code tests: 15 Python cases (actual weekly generation and
shared processor/search functions, real executor threads and controlled HA,
catalog and storage boundaries), 29 Node cases, and 12 Chromium scenario groups
at 390x844 and 1366x900 with the real v143 ETA layer plus the new weekly mixin.
An empty-plan fixture generates 21 distinct slots and reports catalog progress
before any plan write. Cancelling during search does not persist an empty or
partial replacement. Zero candidates and catalog failures terminate cleanly.

The empty-plan regression fails on the hash-verified previous generator because
its search callback is missing, and passes with this patch. The browser test also
reproduces the old estimator returning 3000 ms after 65 seconds at 0/1 while the
new display correctly reports elapsed time and lack of a progress update.

Read-count tests prove identical candidate outputs with one nutrition snapshot
pair instead of a pair per recipe. This is not a live-server timing benchmark.
The existing weekly-responsive/variety tests also pass locally; current full
repository regression workflows run on the PR before merge.

Local sources were recovered from the retained repository backup; all four
modified existing files were checked against current v199 Git blob hashes before
patching. Only this explicit delta is published over current main. No copied
older catalog, pricing, receipt or filter implementation is published.

No live Home Assistant, real user inventory, external price provider or actual
camera/AI Task was accessed. This fixes proven progress/ETA faults and redundant
copying; it does not establish the total generation time on the user's server.
A large filtered catalog can still take longer than five seconds.

## Run

```sh
python tests/test_week_progress_v200.py
node --test tests/test_week_progress_v200.mjs
python tests/browser_week_progress_v200.py
```

Home Assistant must receive the current source and restart/reload before testing
this change. Manifest remains `2026.9.22.7`; active runtime revision is `200`.
