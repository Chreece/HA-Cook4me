# Selected filters, missing recipe positions and camera layout — v202

## User-visible changes

Selected checkbox items in recipe filters (ingredients, languages and meal types)
move to the top of their own list. Both groups retain their original relative
order. Existing DOM controls and their handlers are moved, not recreated. Focus
is retained. Alias-aware ingredient search remains inherited; selected ingredients
remain visible while searching and become subject to search again on deselection.
The per-view filter store introduced in v199 is unchanged.

Daily results show a separate placeholder for each explicitly reported missing
meal category. Weekly responses now retain unavailable saved-slot metadata and
the expected positions from the actual weekday pattern and course filters.
The view displays those positions chronologically instead of silently dropping
them. The message distinguishes unavailable saved data, processing failure,
filter exclusion, no returned match, and an unplanned meal. These are information
cards, not actionable recipes: no send/apply controls, fictitious ingredient data,
stock reservation or zero-price assumption is attached. A notice states that
summary totals and shopping requirements cover loaded recipes only.

The shared recipe-card renderer also isolates individual unreadable/render-failing
records so other cards survive. Pagination and deliberately filter-hidden cards
retain their existing semantics. A short final search page does not get padded to
eight cards, and unknown provider omissions are not invented from a global total.

The receipt-camera button uses the published `mdi:receipt-text-outline` icon. Its
location beside Nutrient scan and its AI-availability rules remain unchanged. The
receipt mode has no alignment guide, corner marks or dimming mask; it previews
the complete video frame with `object-fit: contain` and captures the full original
frame. Barcode/date/nutrition/product guides and crop behavior are retained.

The camera height follows the usable viewport instead of forcing a 520–530px
minimum. Landscape mode compacts the header and keeps capture controls accessible.
Window/visual-viewport resize, screen orientation and video intrinsic-size changes
update the existing preview without reopening the stream, resetting product
assignments or losing receipt edits. Listeners and observers are disposed on close.

## Backend and distribution boundaries

`weekly_plan.refresh_plan` records per-slot ValueError/TypeError/KeyError failures
instead of aborting siblings. The normal filtering path still uses one batch;
only a malformed batch is retried per recipe to isolate failures. Network, storage
and cancellation exceptions are not suppressed as parsing errors. Filtered meals
remain ineligible, including unsafe leftovers. Missing-card metadata contains only
slot identity, date, meal type, selection and a fixed reason code, not raw exception
payloads or recipe details filtered out by dietary rules.

Saved plans and inventory are not rewritten by the presentation change. Existing
pricing/stock rules, receipt drafts, manual Save/Discard, per-view filters, weekly
progress and the reduced HACS archive remain in place. Runtime URL and active
constructor advance to v202; the manifest version is unchanged.

## Validation

Before publication: 17 production Python presentation tests, 23 JavaScript tests,
26 Chromium scenario groups across 390x844 and 844x390 (including rotation of the
same open scanner) pass. An additional 128 retained JavaScript and 15 retained
weekly-generation Python tests pass in the local bootstrap checkout.

Browser checks run the new production mixins and inherited scanner CSS with
controlled HA/API/video and base-renderer boundaries. They check DOM order, focus,
retained handlers, missing-card isolation, guide removal, control geometry, source
crop selection and observer cleanup. They do not emulate real camera hardware or
fetch the HA icon font. The icon identifier is verified against its upstream page:
https://pictogrammers.com/library/mdi/icon/receipt-text-outline/
Video resize behavior is documented at:
https://developer.mozilla.org/en-US/docs/Web/API/HTMLVideoElement/resize_event

Local source was bootstrapped from the retained repository bundle plus the verified
v200 files. The three modified runtime files were checked against current GitHub
blob hashes. Publication applies only the explicit delta to current v201's tree;
no older catalog, pricing or other source files are republished. Existing current-
repository checks and the new Menu gaps and scanner layout workflow run on the PR.
No live Home Assistant deployment, inventory access, physical camera or AI-provider
recognition test has been performed.
