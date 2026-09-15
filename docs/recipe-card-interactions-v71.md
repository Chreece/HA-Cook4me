# Recipe cards and removal (v71)

The shared recipe card now centers its translucent action buttons along the
photo's lower edge. Title, background and other non-control areas open the same
fullscreen dialog as the photo. Enter/Space work when the card itself has focus.
Buttons, inputs, dropdowns, disclosure summaries and text selection keep their
own behavior; one click produces one open operation.

Collapsed cards use a 310 px height, with an 88 px title area and 220 px photo
area (plus borders). Expanded cards use 600 px and scroll their detail area.
Widths remain responsive to the current grid, including the seven-day planner.
These sizes also apply when the photo is missing. Titles are measured after
rendering and on resize, using 12–20 px text. Extreme titles retain a readable
minimum and a four-line limit, with their full text in the tooltip and dialog.

## Removal fixes

- The legacy book renderer classified every unfamiliar source as a custom
  recipe. Official offline favorites could receive a local Delete action, even
  without the local `id` required by that endpoint. Source IDs now establish
  official identity independently of the source label.
- Saved collection cards have a Remove from favorites/list action. Fullscreen
  retains the originating collection for this action. Removing a favorite does
  not delete a locally created original or its entry in another collection.
- Explicit collection removal is idempotent and uses the persisted `bookKey`.
  Hydration/translation can no longer turn removal into adding a duplicate.
  The frontend now uses the backend's `v:` prefix for variant identities.
- Deleting an actual local recipe removes its saved copies from favorites and
  the recipe list, including stale copies from earlier deletions. Unrelated
  recipes and official publications are retained. The UI adopts the returned
  collection state immediately.

## Verification

- Five Python checks exercise the real book/hub stores and production delete
  and book websocket handler bodies with HA storage isolated. They cover saved
  identity changes, repeated removal, collection boundaries, local deletion,
  preservation of unrelated official entries and persistence after reload.
- A DOM regression checks title/background/photo/keyboard opening across
  Today, Week, Official, My recipes and Book; control isolation; official
  favorite removal; fullscreen collection removal; local favorite deletion;
  centered controls; fixed geometry declarations; and title-fit bounds.
- Existing shared UI, catalog, recipe layout, actions, photo overlay and
  fullscreen translation suites run on the v71 bundle.
- The installer retains pinned source, preflight, backup, rollback and exact
  served-panel verification. Reload the panel after installation.

This workspace has no connection to the user's HA host and no graphical
browser. DOM tests exercise event behavior; title-fit tests provide layout
metrics explicitly. Pixel rendering and physical-device operation are not
claimed as verified here.
