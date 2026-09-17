# Product review and editable packages — v112

Panel build: `2026.9.17.16`.

The recognized product remains active until Apply succeeds. Clicking the camera,
changing label modes or presenting another barcode cannot discard the active
product. Date and nutrition modes allow direct manual entry by tapping their box;
AI corrections and label scans attach to the same draft. Apply sits at the lower
right of the camera and is the only action that saves the product and enables
the next barcode. The camera stream stays active. A barcode still visible just
after saving is ignored until it leaves the frame or a different barcode appears.

The product card uses the matched offline ingredient's localized name, with
package amount/unit, existing stock and named storage places. Clicking it opens
the full editor inside the camera. Package identity, brand, barcode, quantity,
unit, ingredient mapping, storage, dates, nutrients and paid price are editable.
Automatic prices remain estimates; entering a paid price records a purchase.
Existing package prices retain their price basis, which can also be edited.

A package-count selector defaults to one. Three 500 g packages ADD 1,500 g to the
existing stock and create three distinct package IDs. For example, existing
750 g plus three 500 g packages becomes 2,250 g. Each new package inherits the
reviewed label, expiry, place and per-package paid price. Retries preserve the
entire batch's identity and cannot add the batch again. Up to 100 packages can
be added with one review. Subsequent package editing is individual.

Stock is grouped into initially folded unique ingredients with localized names
and aggregate amounts. Expanding a group exposes each package; clicking one
opens the full editor with its exact saved nutrition and price. A single package
can be reassigned, corrected or removed without replacing its siblings. Unknown
and unlimited legacy stock retain their existing controls. Quantities with
incompatible units stay separate in the aggregate display.

Package edits compare a saved version and persist a retry receipt. A stale edit
or retry cannot overwrite a newer package version. Inventory writes are staged
before replacing live state. If a dependent nutrition or price save fails, the
same request finishes those details without creating another package. Exact
nutrition and price can be cleared, including zero nutrient and zero-price values.

Validation:

- Eleven backend cases cover multiple distinct packages, additive quantities,
  per-package nutrition/prices, durable retries, partial failure recovery,
  reassignment with sibling preservation, stale edits, failed storage writes,
  clearing details, individual removal, price replacement and authorization.
- Actual bundled-panel browser checks with a synthetic camera and mocked
  providers cover product locking, manual label entry, AI corrections to the
  same product, full editable details, localized card labels, additive multi-pack
  capture, immutable retry, next-product isolation and grouped package editing.
  Phone layouts were inspected and checked for overlap.
- Existing capture, automatic price, inventory, nutrition-inventory and weekly
  selection tests pass. Header/navigation checks cover the inherited views.
- The installer runs staged checks, backs up the integration and supports
  rollback; its success and failure paths are tested without a real host restart.

Browser barcode capabilities and the configured Home Assistant photo provider
remain prerequisites for their respective scan modes. No live phone camera or
Home Assistant host was available here for hardware verification.
