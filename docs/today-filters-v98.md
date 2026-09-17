# Today persistence, suggestion rotation and filter controls — v98

Build `2026.9.17.2` follows the complete v97 runtime and retains its offline price evidence.

## Resuming Today

The browser's compact card snapshot kept score fields but discarded the diet-check fields required by the current card renderer. After navigating away and recreating the panel, vegetarian/vegan/pescatarian cards could therefore be hidden. The idle snapshot write could also be cancelled by an immediate navigation.

v98 retains diet, exclusion-signature and substitution evidence through repeated browser compaction. It flushes the small snapshot when suggestions finish and when the panel disconnects. Saved household selections remain intact while the lightweight bootstrap has no profile data. Existing pre-v98 browser cards with missing diet evidence recover from Home Assistant's saved plan when that plan passes the current checks; reopening never generates a replacement suggestion set. Browser snapshots remain scoped by user and device.

The HA Today store also retains exclusion signatures and meaningful empty results. Compact cards still omit full ingredient lists and instructions. Diet checks are not relaxed.

## Suggestion variety

The previous picker excluded only the last recipe for each category, allowing an A/B/A/B loop. v98 keeps the last 256 suggested recipe-family identities and catalog languages in the HA Today store. It prefers eligible families absent from that history, balances represented catalog languages, and uses the least recently suggested eligible family when a category has exhausted its choices. Score ranking breaks ties within those choices.

All existing diet, ingredient, pantry, nutrient, cost and recently cooked-meal filters run before selection. Suggestions remain distinct families within each plan; a translation or serving edition is not treated as a new recipe. Suggestion history is separate from cooked-meal history and survives an HA store reload.

The real offline test selects only the vegetarian diet with all 21 official catalog languages enabled: **6,188 eligible families**, **three consecutive eight-category plans**, **24 distinct selected families** and representation from all 21 catalogs across those plans. The test recreates the HA store between requests. Categories with limited choices can still repeat after their eligible pool is exhausted.

## Filter bar

- Filter and individual filter buttons show icons without visible text labels; tooltips and accessible names retain descriptions.
- Default controls expand directly to the left of Filter, inside its outlined group.
- Nondefault controls move outside that group to the right. Restoring a default value moves the control back into the expandable group.
- Active controls show a positive badge counting selected options. Ingredient, catalog and meal selections use their selection counts; diet/profile/limit controls count the active settings. An explicitly entered zero limit counts as one active setting, so the badge never displays zero.
- Today, Week and Search share the behavior, including narrow layouts and Escape-to-close.

## Verification and installation

Focused verification covers four Today backend tests (including the real catalog requests), four existing catalog-selection tests, a Chromium run of the shipped v98 bundle, and four installer tests. Browser checks exercise actual Today responses, immediate navigation and recreation, restoration of old saved cards, filter dialogs and movement between groups, positive badges, cancellation with a late response, user/device separation, and English/German/Greek layouts at 360, 390 and 1600 pixels. Build freshness, Python compilation, shell syntax and whitespace checks also pass.

The standalone installer is pinned to the reviewed runtime in a follow-up commit. It validates the staged files and runs the focused Today suite before stopping HA, then retains the existing backup, 120-second stop timeout, served-panel verification and rollback. No live Home Assistant deployment was performed here.
