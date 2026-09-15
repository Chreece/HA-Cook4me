# Catalog results and progress, v64

Today and Official returned empty lists because the shared meal-type filter
rejected every compact offline row: the release contains no provider course or
occasion taxonomy. Selecting all eight categories now means no category
restriction, including recipes whose category is unknown. Explicit `mealTypes`
and provider taxonomy are respected, and available provider taxonomy survives
row materialization.

For the existing release, specific category filters use conservative dish-name
rules against the assistant-reviewed English canonical title. These are marked
`mealTypeSource: canonical_title`; they are not SEB course metadata. Ingredient
words do not classify dishes, and uncertain titles remain unclassified. Thus
individual category filtering is intentionally incomplete until provider course
data is available. This does not limit searches with all categories selected.

Today sends one request containing every selected category and catalog language.
The server filters the catalog once, chooses distinct recipe families, rotates
away from the previous suggestion when alternatives exist, and saves the full
category plan. Empty categories receive a visible explanation. Stored cards keep
their category and family identity. Canonical ingredient names participate in
diet checks so a French lamb recipe cannot pass a vegetarian filter merely
because its displayed ingredient is in French. Request-specific diet settings
no longer mutate the household profile.

Catalog materialization, ranking and nutrient filtering publish measured counts
through the existing bottom-right progress popup. Executor events are marshalled
to Home Assistant's event loop. The frontend request owner completes a job only
after receiving and rendering the response; a server completion event cannot
finish a parent action early. The old inline loading banner is suppressed and
section refreshes reuse the current task. Failures retain their error state.

The active frontend is the isolated v64 bundle, build `2026.9.15.6`. Existing v63
Greek ingredient labels, shared controls, per-user menu preferences, recipe
dialogs and device-send identities remain available. No Ollama or translation
service is called by this change.

Validation includes the real offline catalog through the Today and Official
WebSocket handlers, actual executor progress and a DOM test that clicks the
Today button and consumes those real backend responses. With German, English,
French, Spanish and Italian catalogs, all eight categories and a vegetarian
filter, Official returns six ramen families and Today returns seven distinct
category cards, with an explicit no-match outcome for Snack. Stock-only searches
with empty stock still return no recipes. DOM coverage also checks delayed
completion, errors, empty results, entry changes, and the existing shared-control
and recipe-dialog suite against the v64 constructor.

`tools/deploy_offline_runtime_v64.sh` installs a pinned runtime commit. Before
stopping Home Assistant it runs offline, presentation, shared-filter and real
catalog-flow checks inside the user's container. It keeps the previous
integration, restores it if activation fails, and checks that Home Assistant
serves the exact installed bundle. Deployment on the user's system still
requires running the installer there; local backend/DOM checks are not a device
visual test.

Published runtime: `fee2553535b23c1486e87cdf17ef807b564ebdaa`. The full Python
suite ran 1,201 tests: 1,190 passed and the same 11 historical nutrition-review
assertions in batches 42–50 failed as in v62/v63. No new failing assertions were
introduced. The final pinned installer also passes its isolated backup,
activation-failure, missing-locale and mount-validation checks.
