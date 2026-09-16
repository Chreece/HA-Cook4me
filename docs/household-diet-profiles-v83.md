# Shared recipe toolbar and household diet profiles (v83)

Today, Week and Search recipe put their existing title, action and search controls
beside the shared filter buttons, in one card. The controls wrap on small screens.
The seven section icons from v82 retain their order and names.

## Profiles in My kitchen & preferences

Diet preferences now contain a general household profile and a separate expandable
section for each household member. A member has a stable ID, editable name and icon.
New members start with a copy of household preferences; later changes are independent.
Selecting Whole household uses the explicitly configured general profile, rather
than combining or averaging member settings.

Each profile contains:

- Diet and nutrition goal.
- Optional targets per serving for calories, protein, carbohydrates, fat, saturated
  fat, sugars, fibre, salt and sodium. Unknown values remain unknown; targets rank
  recipes by proximity, not by treating missing nutrients as zero. Existing catalog
  and calculated nutrient field names are both supported.
- One list of excluded ingredients for allergies and avoidance. A searchable dropdown
  exposes the full available ingredient catalog and preserves catalog identities and
  source aliases across languages. The options are rendered when the picker opens.

Existing free-text allergies and avoid entries migrate without disappearing. They
remain removable exclusion chips even if they cannot be mapped to a catalog item.
Existing member names remain available for meal portion allocation and history.
Changing a member's name does not change their profile ID. The old profile fields
are maintained for other integration features and older clients.

Preferences belong to the Cook4Me household/device. A dedicated authorized endpoint,
`cook4me/v35/diet_profiles`, saves them without replacing stock or storage locations.
Editing drafts survive re-renders and failed saves; drafts are cleared on account or
device changes. A late save response cannot replace another account's editor.

## Applying a profile

The first button in the shared filter bar opens Diet profile: Manual, Whole household
or a named member. Choosing a saved profile copies its values into the diet,
nutrition and exclusion controls. Exclusions are editable from the diet button.
Manual keeps the current values and permits independent edits.

Applying an actual change through a filter button switches the source to Manual.
Applying unchanged values keeps the selected profile, including after numeric values
have been normalized by the server. Diet/meal tags also switch to Manual when they
change the active filters. The source and explicit filters persist with the existing
per-user, per-device UI preferences. Existing manual nutrient filters are retained
when migrating older UI preferences.

Saved selections resolve against current server profiles before search/planning,
fullscreen presentation and delivery. Exact exclusions are hard gates, including
translated catalog aliases and substitution candidates. Existing diet substitution
rules remain unchanged. Unchecked cached cards cannot be reused as proof after
exclusions change, and late recipe responses are rejected after a profile change.
The original official cooker program remains the program sent to the appliance.

Queued sends retain the selected profile and recheck it before delivery. A removed
member blocks queued delivery instead of falling back to another profile. In the UI,
removing the selected member switches to Manual with the last explicit values.
For a different target device, the sender carries an explicit Manual snapshot because
member IDs belong to the selected household/device.

## Verification

Real Chromium exercises the combined toolbars, full 3,000-item fixture dropdown,
independent profiles, nine targets, migration chips, name/icon editing, draft retention,
save failure/retry, manual reset, unchanged Apply, deleted-member handling, stale
fullscreen responses and account isolation. Layout bounds are checked at 360/390 px;
English, German and Greek profile layouts are checked and screenshots inspected.

Python tests cover migration and persistence, independent server-side resolution,
exact exclusions, excluded substitutes, nutrient aliases and zero targets, endpoint
authorization, the shared ranking pipeline, immediate sending and queue replay.
The existing v82 navigation/creator/price-refresh, v80 scanner and v79 pricing browser
suites also pass on v83. API responses and appliance delivery in tests are fixtures;
no live Home Assistant instance or appliance was accessed.

Active panel: v83. Cache path: `2026.9.16.8`.

All 1,461 Python tests passed in the full regression run. The ten focused profile
tests also passed after the final migration and large-exclusion checks. Bundle,
JavaScript/Python syntax, workflow YAML, version and diff checks passed.
The real English catalog exposes 3,680 choices; its largest linked alias set is
137 entries. Cancelled filter dialogs and normalized numeric values are covered
by browser checks so they do not spuriously change a selected profile to Manual.
