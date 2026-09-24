# Recipe actions, storage visibility and USDA fallback review — v218

This batch addresses the five user-visible issues reported after the v217 bug-hunt
series.

## Recipe action disclosure stays anchored

The recipe `More` disclosure no longer changes to `flex-basis: 100%` when
opened. Its summary remains at the same position/row and the expanded secondary
actions are rendered inside a bordered surface belonging to that same disclosure.
The original action nodes/listeners are retained; this is a layout change only.

## Recipe ingredients show where matching stock is stored

Recipe ingredient rows now append the names of matching configured storage places
when Cook4Me can prove the stock identity/link. Multiple locations are shown once
each. No location is invented when a stored item has no location.

Matching follows the same stable catalog identities and explicit product links
used by stock coverage; translated display labels are not treated as identity
proof.

## Unlimited stock keeps and uses storage metadata

Unlimited stock previously dropped package metadata because it has no lots. That
meant pantry staples such as salt, pepper or water could exist as unlimited stock
but not appear in a storage-place view, and product-to-catalog links were ignored
by `stock_for_ingredient` because that function only inspected links inside
finite lots.

Unlimited rows now retain reviewed row-level metadata relevant to logical stock:
storage kind/location, product/brand/barcode, container/source and explicit
ingredient links. The stock matcher checks row-level links for unlimited items.
Storage-place rename/delete integrity also includes unlimited rows.

No finite quantity, purchase price or exact package nutrition is created for an
unlimited item.

## Container Use is reversible

The saved-container button now reflects its current action. Pressing `Use`
activates that container tare and changes the button to `Unuse`
(`Ακύρωση χρήσης` / `Nicht mehr verwenden`). Pressing it again removes the
software tare, clears the active container and restores `Use`.

## “Unresolved nutrients” are now reviewable and correctly explained

The number shown in the nutrition settings is not the reviewed Cook4Me offline
catalog being incomplete. It is the optional local USDA FoodData Central fallback
cache used only when Cook4Me has no usable reviewed/exact generic nutrition for
an ingredient.

Negative USDA results are deliberately cached so ambiguous candidates are not
silently guessed and DEMO_KEY quota is not repeatedly consumed. v218 exposes the
active negative-cache rows in the UI with the ingredient/query, failure reason
and automatic retry time.

Each active row now supports:

- **Retry now** — clears that one negative-cache record and performs one fresh
  strict USDA lookup immediately.
- **Manual nutrition** — stores user-verified values per 100 g or 100 ml for that
  exact catalog identity, then clears the unresolved record.

Manual values go through the existing generic-nutrition validator and require at
least one non-negative nutrient value. They do not modify exact scanned-product
nutrition.

The old labels are also clarified: the panel is called an optional USDA fallback,
the batch button tries the next USDA fallback batch, and blocked rows are described
as matches needing review rather than “temporarily unresolved”.

## Runtime and regression coverage

Frontend runtime rotates from v208 to v218 so Home Assistant cannot reuse the old
long-lived custom element.

New regressions cover:
- unlimited stock metadata and linked-catalog matching;
- storage-place delete/rename integrity for unlimited rows;
- scanner unlimited metadata handoff;
- active unresolved nutrition review rows;
- v218 route/runtime wiring;
- anchored/grouped More layout;
- Use -> Unuse container state;
- full-browser storage labels, unlimited storage visibility, container toggling
  and immediate unresolved-nutrition retry.

No live Home Assistant instance, USDA request, inventory, scale, camera, AI
provider or cooker is accessed by these tests.
