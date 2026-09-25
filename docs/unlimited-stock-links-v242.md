# Unlimited stock catalog assignments — runtime v242

Existing unlimited items now have a searchable **Assigned catalog ingredients**
section inside their stock card. Open the item, select its additional ingredients
and press Update. The main stock identity remains assigned; additional links can
be added or removed. Greek, German and English labels are included, and catalog
names follow the existing UI/supermarket naming logic.

The picker is built only when expanded. Selecting a checkbox keeps its position
and the list's scroll position. Selected ingredients remain visible while
searching. Assignments are drafts until Update; saving disables the controls,
and a failed save keeps the draft available for retry. Removing the stock item
clears its pending assignment draft.

The existing inventory-update route accepts optional `ingredient_links` for
unlimited items, validates them against the cached offline catalog, resolves
source identities and deduplicates them before the durable stock write. Omitting
links preserves existing assignments; an explicit list replaces them. Location,
product metadata and expiry remain intact. A measured-to-unlimited conversion
also retains existing package links when no replacement list was supplied.
There is still one unlimited stock item, without invented quantities or lots.

Both ingredient-presence matching and quantity coverage recognize the assigned
identities. The scanner's existing-stock preview includes linked unlimited
items, and cooking consumption cannot deplete them. New unlimited products
continue to use the existing scanner multi-assignment flow.

Local validation: seven focused persistence/route/coverage tests, fifteen durable
mutation tests, thirteen stock/runtime tests, twenty-eight stock-coverage tests,
seven unlimited-stock regressions and fifty-five product-editor JavaScript
checks. Browser checks use the full shipped Greek catalog at 390 and 1440 px,
covering selection/removal, save/reopen, retry, linked stock preview, scroll
position and preservation of one unlimited item. No live Home Assistant stock
was modified during testing.
