# v93 — Cancellable jobs, compact filters and time-aware Today

The lower-right progress window now has a Cancel button for each running job.
Cancellation immediately releases the UI, stops the corresponding asynchronous
server requests and prevents their late responses from replacing the current
results. Queued requests and subsequent batches sharing the cancelled job ID are
also rejected. Cancellation is scoped to the authenticated connection that
started the job, even when another connection uses the same user and job ID.
Already completed writes are not undone; a synchronous executor call already
running may finish internally, but its cancelled request cannot apply its result.

The cancellable endpoint uses only existing registered Cook4Me commands, their
original schemas and their original authorization checks. Synchronous commands
or commands with outer permission wrappers retain their original endpoint.

Today, official search and the weekly plan share the updated toolbar. Menu
controls are on the left. Active filter buttons are on the right, with member
icons and selection counts or values. Default filters are available through the
Filters drawer. Drawer buttons keep the existing filter dialogs and preference
persistence. Omnivore alone is no longer incorrectly marked as a diet filter.

Today shows a localized date, clock and meal period in Home Assistant's configured
time zone (falling back to the browser's zone). The display updates every 15
seconds without rebuilding the recipe list. Meal periods are:

| Local time | Period |
| --- | --- |
| 05:00–09:59 | Breakfast |
| 10:00–11:59 | Morning snack |
| 12:00–14:59 | Lunch |
| 15:00–17:59 | Afternoon snack |
| 18:00–21:59 | Dinner |
| 22:00–04:59 | Late snack |

Labels are available in Greek, German and English. Today cards for another meal
period are greyed out and marked accordingly. Their controls remain enabled;
hover or keyboard focus restores full contrast. Main courses, starters, salads,
soups and sides fit lunch/dinner; desserts also fit afternoon snack time. Recipes
without a known meal category remain undimmed. The clock timer is cleaned up on
navigation away from Today or disconnection.

## Build-specific validation

- `tests/test_jobs_v93.py`: running and queued cancellation, early cancellation,
  continuation batches, connection isolation, original schema/authorization,
  response IDs and outer permission wrappers.
- `tests/frontend_v93_jobs_toolbar_browser.mjs`: real bundled Today/Search/Week
  rendering, active filter indicators and drawer, cancellation through the real
  API layers, UI recovery, late responses, overlapping jobs, localized clocks,
  date rollover, all period boundaries and a 390px toolbar.
- `tests/test_deploy_offline_runtime_v93.py`: installation and rollback gates.
- `tools/build_frontend_bundle_v93.py --check`: reproducible scoped frontend bundle.

The installer runs only the v93 cancellation test module, plus the existing
artifact-presence/offline preflight and activation gates. No historical pricing
regression suites are added to this UI build. The panel uses build
`2026.9.16.17` and custom element `cook4me-recipe-hub-panel-v93`.
