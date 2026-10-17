# Loaded-recipe navigation and cooking-mode audit — v284

## Verified code paths

- The Home Assistant subscription `cook4me/v32/device_state_subscribe` supplies
  `state.recipeTitle`, `state.variantFunctionalId`, `state.stepFunctionalId`,
  `state.stepIndex` and `state.programName` (source: `websocket_v32.py`).
- The device-info dialog in the inherited v81 panel previously rendered
  `state.recipeTitle` in a plain `<dd>` (not a link).
- The existing official fullscreen path is `_showRecipe(recipe, false)`; it
  requests the chosen display variant via `cook4me/v31/recipe_detail`.
  No new service/API is needed.
- Recipe-step programs originate from the SEB step's
  `sequences[].operations[].program.{key,name}`, filtered to Cook4Me
  appliance group `APPLIANCE_GROUP_15`. The v259 mode translator recognizes
  explicit source names and descriptive keys, but does **not** infer a numeric
  `PROGRAM_n` identity. An unrecognized nonempty name is deliberately displayed
  as "Other cooking mode" (localized).

## Changes

1. The device info recipe value becomes a keyboard-accessible button when the
   actual authorized live state contains a nonempty `variantFunctionalId`.
   The existing fullscreen official detail loader is used with that exact
   variant; a recipe title is **never** treated as unique identity.
2. Clicking a link from a stale device or after an entry/user change does
   nothing. Unauthorized/offline/missing-variant values remain read-only.
3. v81 now caches the source HTML rather than comparing against user-enhanced
   HTML so a focused link survives routine subscription refreshes.
4. Mode normalization adds the explicit source phrase `Warm holding` (and exact
   synonyms). High-pressure cooking was already known in English, German,
   Greek and French.
5. For the *loaded variant's current step only*, if the published step has no
   recognized program (including "Other cooking mode"), the UI may display
   the cooker-reported `state.programName` translated to UI language. The
   tooltip identifies it as **live-device evidence**, not a source recipe
   program. This is never applied to a different variant, stale step ID, or
   an already recognized or multi-operation recipe step.

## Mode consistency matrix

| Evidence | Expected label in Greek UI | Decision |
| --- | --- | --- |
| Source `High pressure cooking` | Μαγείρεμα σε υψηλή πίεση | Known recipe program |
| Source `Druckgaren` | Μαγείρεμα υπό πίεση | Known generic pressure |
| Source `Warm holding` | Διατήρηση θερμοκρασίας | Known keep-warm |
| Source `Mantener caliente` | Διατήρηση θερμοκρασίας | Known keep-warm |
| Unknown `PROGRAM_999` with no source name | Not specified | Never infer ID |
| Unknown source name in inactive recipe step | Άλλη λειτουργία μαγειρέματος | Do not borrow live status |
| Unknown source name in loaded *matching current step* + live `High pressure cooking` | Μαγείρεμα σε υψηλή πίεση | Live evidence, tooltip |
| Same exact step + live `Warm holding` | Διατήρηση θερμοκρασίας | Live evidence, tooltip |
| Live `phase=keep_warm` but no `programName` | No inferred mode | Phase is not a program |
| Explicit multi-operation step | Its listed programs | Never overwrite with one live mode |

## Validation and limits

Focused checks exercise official variant targeting, UI localization, exact step
identity, missing/stale device guards, and keyboard/button wiring. They preserve
historical v259 behavior. The v284 registration and module query prevent
Home Assistant/browser custom-element constructor reuse after update.

The user's reported wording alone does not identify the underlying program ID
or localized source program name; do **not** introduce a hardcoded numeric
`PROGRAM_n` mapping. A final live UI check while the cooker is running is
still required before public release.

Only frontend files and the panel registration change. Appliance state,
storage, inventory, credentials and cooking commands are untouched.
