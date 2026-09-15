# Shared Recipe Hub controls and bundled Greek catalog

The active panel is v63, build `2026.9.15.5`. Install with
`tools/deploy_offline_runtime_v63.sh` as a standalone `sudo bash` script.
The installer pins the tested runtime commit, validates before stopping Home
Assistant, retains the previous component, and rolls back on failed startup or
runtime probes. It checks that Home Assistant serves the exact installed bundle.
Do not source the script into an interactive shell.

## Offline Greek ingredient names

All 3,713 cleaned source names now have assistant-authored Greek labels in
`catalog_ui_locales/el.json`. No translation service, local model, model download,
or translation preparation is needed during installation. The picker merges
identical translated names into 2,948 choices and omits 33 reviewed fragments
that do not identify a food. Food specifications, including cream percentages
and flour types, remain in the names. Source records and nutrition bindings are
unchanged. Every merged choice retains its own provider identity and the source
IDs of its display aliases; matching by translated labels cannot transfer a
nutrient profile from one ingredient to another.

Presentation version 63 invalidates cached pre-translation ingredient lists.
Labels follow the Home Assistant UI language; this update completes the Greek
locale. Other UI languages retain their existing labels and provider translations.
Automatic recipe-text translation is disabled, and its old toggle is removed.
Recipe language/quantity selectors still load the original text for that exact
publication. Explicit AI recipe features remain available.

The v62 ingredient-nutrition contract remains in use. Known catalog profiles are
shown by original ingredient ID. Generic rice still has no reviewed profile;
its popup shows separately labeled reference values for specific rice types.
Those references do not become generic-rice nutrients or enter recipe totals.

## Common filters and recipe dialogs

Today, Weekly and Official use the same seven-icon row: diet, meal categories,
source languages, ingredients, home availability, nutrition targets, and cost.
The separate home-availability tab is removed. Labels remain available through
tooltips and accessible names, and the controls fit one row on narrow screens.
Weekly's calendar icon is present whether selected or unselected.

All three sections use the stored diet-profile and inventory ranking rules.
Shared filtering runs over the matching offline recipe families before result
pagination or plan selection. The old 30-result recommendation limit remains
for its existing callers; the shared path explicitly ranks all candidates.
Ingredient selection uses source IDs, including the aliases of merged display
choices. Home availability requires sufficient known stock quantities.

Energy, protein and fibre targets rank recipes by known values per serving;
missing nutrients remain unknown. A maximum cost per serving requires complete
price coverage in the selected currency; unknown costs are not treated as zero.
Weekly scheduling, daily dashboard targets and purchase-price settings remain
available under the separate calendar-settings button.

Clicking a recipe in Today, Weekly, Official, saved recipes or ingredient usage
opens the same dialog with ingredients, steps, nutrition, costs and existing
actions. Keyboard activation, Escape, focus return and focus containment are
supported. Language/quantity changes fetch exact variant details inside that
dialog. Send controls require a proven send identity. Late responses cannot
replace a newer variant or reopen a closed dialog. Leftover records retain their
original recipe; older leftovers can recover the recipe identity from meal
history when it is still available.

## Preferences and background work

Home Assistant stores the last selected section and shared filters per
authenticated user and integration entry. A second browser/device restores the
same choices. Local storage is an offline cache; pending changes retry on
reconnect or returning to the app. A delayed preference read cannot overwrite a
newer navigation choice. This does not force another active device to change its
section while its user is browsing.

Background messages use the existing bottom-right popup appearance. Concurrent
jobs retain separate progress cards; official catalog searches and cache refresh
messages no longer insert a progress banner above the search form.

## Verification

The full Python suite ran 1,192 tests: 1,181 passed and the same 11 historical
nutrition-review assertions failed in batches 42–50. A subsequent focused test
also verifies the actual shared ranking path retains matches beyond the old
30-result limit. New tests cover complete Greek label coverage, merged source
identity preservation, combined stock/ingredient/cost filters, target ranking,
pagination, persistent user isolation and installer rollback without Ollama.

DOM tests instantiate the generated v63 bundle and exercise the shared controls,
weekly recipe clicks, dialog actions, exact variant changes, stale-response
guards, second-browser preference restoration and concurrent progress. The v62
stale-constructor and ingredient-nutrition regression test still passes.
`python tools/build_frontend_bundle_v63.py --check` verifies the committed bundle.
No physical phone/browser rendering or homeserver deployment was available from
the development workspace; the installer performs the target-side checks.
