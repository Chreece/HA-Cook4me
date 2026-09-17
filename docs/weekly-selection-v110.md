# Weekly recipe selection — v110

Panel build: `2026.9.17.14`.

Every weekly recipe has a checkbox in its title. Existing and newly generated
meals default to selected. Selections are saved with the plan and survive reloads.
Unchecked meals stay visible but do not contribute to stock reservations, daily
or weekly nutrient/cost totals, or the plan's purchase requirements.

Day checkboxes select or unselect the visible meals for that day and show a mixed
state when appropriate. The seven-day generator is now an icon. Beside it are
select all, regenerate selected, unselect all and regenerate unselected icons,
with translated tooltips and accessible labels. Bulk actions operate on the
current shared-filter view; hidden saved meals retain their selection.

Regeneration makes one batch request, keeps slot IDs and checkbox states, avoids
duplicates across retained and replaced meals, and preserves recipes when there
is no different matching candidate. Concurrent plan edits cause generation to
stop without overwriting the newer selection or recipe.

Reserved stock is an expandable list of ingredients whose combined selected
requirement is fully covered by known inventory, including unlimited supplies.
Plan shopping expands to show aggregated shortages and quantities. An ingredient
absent from inventory has zero stock and now correctly produces a purchase
requirement. Existing inventory with an unknown amount or incompatible unit is
shown separately for checking, without inventing a purchase quantity. Leftovers
do not reserve their original raw ingredients again. Original ingredients of
unfinished dietary adaptations retain the existing purchasing safeguards;
unchecked adaptations do not block purchases for checked recipes.

Validation:

- Eleven backend tests cover persistence, old-plan defaults, selected-only cost
  and stock arithmetic, absent versus unknown inventory, filtered views, request
  handling, bulk replacement, no-match preservation and concurrent edits.
- Real bundled-panel browser checks exercise per-recipe/day/all checkboxes,
  mixed states, both regeneration groups, zero totals, stock/purchase dropdowns,
  reloads, failed-save rollback, shared filters, stale responses and responsive
  Greek/German/English layouts.
- Existing lifecycle, weekly variety, rolling-week and weekly-summary suites
  pass. The installer preflight suites for pricing, entity setup, device
  announcements, language-independent sends, dietary guidance and delivery
  confirmation also pass.
- Header/navigation checks cover seven views, three languages and four widths.
  Installer tests cover staged validation, backups, activation and rollback.

Home Assistant and appliance access are unavailable here; installation and live
device operation must be verified on the user's host. This change does not claim
to fix the previously reported appliance firmware exception.
