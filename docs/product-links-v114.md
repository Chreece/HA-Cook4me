# Product catalogue links and stock names — v114

Panel build: `2026.9.17.18`.

Restart stays visible immediately beside Apply in every scanner mode. It can
discard an unsaved review, cancel a pending recognition and start a new barcode
scan without reopening the camera. Late recognition responses are ignored.
During a stock write it is temporarily disabled. If a save returned an uncertain
result, Restart first retries the same immutable request and advances only after
the save completes, preserving all package details without adding them twice.

The product editor offers a searchable checkbox list of the complete offline
catalogue. One product can supply several selected catalogue ingredients. These
are user-reviewed associations, not quantities or proportions of a mixture.
The backend validates every link against the catalogue, deduplicates it and
persists it on each package and in the remembered barcode mapping. Existing
single-ingredient packages continue to work. Links can be changed individually
when editing a package; details are localized without changing its saved version.

There is one physical quantity per package. Linked ingredients share the same
lot IDs and available amount for stock checks, reservations, shortages, recipe
costs, exact nutrition and consumption. Each calculation allocates available
stock in expiry order; a lot already allocated to one ingredient cannot also be
counted in full against another. Price-cache fingerprints include the links.

Stock is grouped by the scanned or manually entered product name. Headings and
individual packages show `Product name (Catalogue ingredient, Other ingredient)`;
catalogue names and amounts use the UI language. Groups start folded and display
the total of their physical packages. Expanding a group exposes each editable
package, its quantity, storage place and expiry. Changing the displayed product
name does not duplicate or replace stock.

Validation:

- Actual bundled-panel Chromium checks cover always-visible Restart, cancellation
  of delayed lookups, recognition restart, multiple searchable selections, exact
  save retries, three additive packages, grouped names, retained editable links,
  and 360/390/1280 px layouts using a synthetic camera and mocked providers.
- Backend cases cover catalogue validation and deduplication, persistence and
  localized readback, barcode recall, individual unlinking, shared reservations,
  shopping shortages, exact nutrition/prices, physical consumption and cache
  invalidation. Existing package, capture, scanner, inventory, nutrition, meal,
  automatic-price, current price-fix and weekly-selection checks pass.
- The older v86 price-coverage suite has one existing seasoning-status assertion
  failure (`recipe_amount_unknown` versus `unmeasured_basic_zero`). The same
  failure was reproduced with the baseline inventory and costing modules.
- Installer checks exercise a simulated host, backups and rollback. No live
  phone camera or Home Assistant host was available for hardware verification.
