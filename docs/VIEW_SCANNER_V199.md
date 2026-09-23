# View filters, fullscreen lifecycle and receipt placement — v199

## Requested behaviour

- Closing a fullscreen recipe with X, Escape or its backdrop clears the owning
  view's saved open-recipe state. Later filter changes, rerenders or navigation
  must not reopen it. A recipe genuinely left open can still restore in its own
  view, never another view.
- Today/daily, Week, Official and the other supported views keep independent
  filters, including nested nutrient targets, diets, languages and ingredients.
- Product scan/edit no longer shows the Saved receipts, Receipt photo or duplicate
  Scan receipt shortcuts above the editor. Saved receipt records are not deleted.
  An active receipt still has its existing review, draft-save and item actions.
- The camera's Scan receipt mode sits immediately after the nutrient-scan mode.
- Receipt photo appears beside Add product in My Kitchen only when the selected
  scanner AI or HA default is an available, permitted image-capable AI Task.
  Its file input selects an existing device picture without starting the camera.

## Fixes and data boundaries

The old fullscreen close listener was attached to an inner button replaced by
recipe-dialog rendering. A delegated listener now lives on the stable overlay.
Open/restore continuations also capture a view, user/entry scope and generation;
a late request or queued restoration cannot restore a recipe closed in the
meantime. Nested ingredient/filter dialogs do not clear the underlying recipe.
One-time migration removes stale saved dialog pointers from earlier versions,
while preserving folds, filters and other view state.

`filtersByView` is stored through the existing authenticated UI-preference route,
under the existing user's entry-scoped preference record. Each view receives its
own deep copy. Legacy shared filters seed independent views once. The backend
normalizes all values with the existing allowlists/bounds and merges partial view
patches under its existing lock. Local edits and pending saves survive reconnects;
late responses cannot overwrite newer edits or another entry's state.

Receipt button visibility uses the backend's permission-filtered image-AI choices,
selected override/default and live unavailable state. No arbitrary provider is
silently selected when an explicit override is unavailable. Recognition retains
its existing backend permission check. File selection, receipt review, privacy,
line-price semantics and durable stock-apply requests stay in the existing flow.
No stock, purchase evidence, recipe quantities or catalog identity is rewritten.
The manual editor's Save/Discard and barcode lookup remain active.

Runtime delivery is bumped to `runtime-v199` with a new active element name, so
HA cannot reuse the cached v198 constructor. The manifest version is unchanged.
No live deployment is performed by this repository change.

## Validation

Local results before publication:

- 31 new Node tests for independent filters, scopes, pending saves, reconnects,
  image-AI eligibility, receipt upload and camera dispatch.
- 11 Python tests of production preference normalization and the actual hub's
  user-preference methods with controlled persistence boundaries.
- 130 combined JavaScript tests passed: the 31 new tests and 99 retained manual
  editor, receipt review and scanner-suggestion tests.
- 24 Chromium scenario groups passed at 390x844 and 1366x900. These exercise the
  production state/scanner code with controlled HA and storage boundaries.
- Reverting the v179 fix makes the first new browser scenario fail: the closed
  recipe reappears after redraw. Restoring the fix makes the suite pass.
- Additional local checks loaded the full existing frontend inheritance chain
  at both viewport sizes, checking the new placement, retained editor controls
  and independent filters with controlled HA/API/camera boundaries.

The View filters and receipt controls workflow runs the new suites. Existing
source, Greek, scanner, receipt, manual editor, consolidation and coverage checks
remain enabled. The older runtime test now verifies that current URL, module
query and active constructor agree instead of pinning all future builds to v198.
Its coverage and identity assertions are unchanged.

Local bootstrap used the retained repository backup plus verified current
frontend files; it was not a full local copy of the latest consolidated catalog.
Remote changes are applied only as an explicit file delta over v198's current
GitHub tree. Full current-repository validation is supplied by the PR checks.
No real camera, AI provider, user inventory or live Home Assistant was accessed.

```sh
python tests/test_view_preferences_v199.py
node --test tests/test_view_filters_v199.mjs
python -m pip install playwright==1.57.0
python -m playwright install chromium
python tests/browser_view_scanner_v199.py
```
