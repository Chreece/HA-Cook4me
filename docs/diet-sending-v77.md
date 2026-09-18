# Sending recipes with complete dietary replacements (v77)

V77 removes the Send restriction introduced in v76 for official recipes that
have a suitable replacement for every ingredient conflicting with the selected
diet. The original recipe remains marked incompatible; it is eligible only
when the complete replacement list passes the current allergy and avoidance
rules.

The cooker receives the original official recipe IDs and cooking program.
Ingredients, appliance instructions, cooking times and nutritional values are
not rewritten. The dashboard displays all replacements and explains that the
user must apply them. This notice is available in English, Greek and German,
with English fallback for other interface languages.

The Send action fetches details for the chosen device and keeps the selected
diet. It rejects a changed user/device context, diet or recipe edition while
the detail request is pending. The backend resolves the official ingredients
again and recomputes dietary eligibility; submitted ingredients and match flags
cannot bypass the check. Target-device allergies and avoided foods still apply.

Offline/busy requests persist the diet with the queued recipe. Delivery checks
the official recipe against the current profile rules again under the send
lock. Existing cancellation, replacement and appliance-state guards remain.
A dietary rejection on the active dashboard endpoint reports failure rather
than being presented as a successful queue operation.

Original incompatible ingredients are still excluded from automatic shopping
and inventory reservations for pending adaptations. This update enables Send;
it does not create a rewritten ingredient list or a custom appliance program.

Frontend: cook4me-panel-v77-bundle.js, build 2026.9.16.2.
Installer: tools/deploy_offline_runtime_v77.sh.
Runtime commit: 5cf5e00c55254c9d8260d6b6de5a9600afa8dc61.

## Validation

- Seven new Python cases exercise original ID delivery, unchanged instructions,
  complete coverage, forged payloads, allergy/avoid rules, queue persistence and
  revalidation, invalid diets, and unchanged compatible recipes.
- The v76 send regression now expects complete adaptations to send.
- The Send DOM test clicks the actual action and checks selected-device detail,
  unchanged ingredients/program, displayed replacements and diet-change races.
- Existing card, dietary cache and asynchronous navigation DOM checks passed.
- Chromium checked 42 cards across six desktop/mobile/expanded layouts.
- An older catalog DOM test assumed exactly two vegetarian ramen families.
  It now checks the full verified backend result, including complete adaptations,
  and explicitly selects the vegetable family for publication/serving tests.
- Full Python suite: 1,367 tests passed in 255.220 seconds.
- All four installer/backup/rollback tests passed after the final runtime pin.
- Catalog flow passed on both the historical v65 and active v77 panels, with
  eight ramen families and seven Today categories.
- Syntax, version, bundle consistency and diff checks passed.
- Published runtime and installer trees were checked against the local trees.

No live Home Assistant or appliance deployment was performed in this workspace.
