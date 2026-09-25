# Saved receipt review

Receipt recognition now saves the parsed lines and queues enrichment in one durable
write before returning success. Closing the panel does not stop enrichment. On
integration startup, queued or interrupted work resumes in a background task;
setup does not wait for product lookups.

The button beside **Receipt photo** shows how many saved receipts still have
pending lines or processing. Expand a receipt to see line quantities, prices,
barcodes, ingredient matches and progress through barcode, nutrition and catalog
matching. Review remains available when the AI provider is unavailable.

- **Edit** opens the existing product form with the receipt values. Package barcode,
  nutrition and date scanning remain available. Barcode scanning preserves the
  purchase price, date and package count. Save changes returns to the receipt list.
- **Add** submits the saved product through the existing stock endpoint. Missing
  catalog identity, package amount or purchase date must be completed in Edit.
- **Discard** permanently removes that line from review. Added/discarded lines do
  not return after reopening. The complete saved receipt can also be deleted.

Enrichment uses existing barcode mappings and Open Food Facts. A search result must
have a unique exact product name and brand, with a compatible printed size, to
supply a barcode. Uncertain matches remain unresolved. Nutrients come from product
records, never guessed from receipt text. Catalog assignments require an existing
saved mapping or one exact compatible match. Only product wording is sent to the
public product search; receipt images, shop, date and payment information are not.
Search is throttled across integration entries. API reference:
https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/

For VAT added to net prices, printed tax groups are allocated in integer cents,
with deterministic remainder distribution. Discounts and deposits retain their own
lines and tax groups, including exempt groups. Allocations must reconcile with the
printed total. Included VAT is never added again. Ambiguous added VAT leaves the
prices unchanged and requires explicit confirmation of the inclusive line price
in Edit before adding it to stock.

Each edited line has its own revision. Opening Edit claims the line so a pending
lookup cannot replace user input; other lines can continue processing. Discards
and inventory additions also prevent late enrichment from replacing the line.
Stock additions retain the existing durable request ID, including after lost
responses or restarts. Discard tombstones are retained privately until receipt
deletion to prevent stale operations from restoring a removed line.

The package weighing action is now inside the package card. The package edit and
weight actions remain separate sibling buttons, avoiding invalid nested buttons.

Validation: receipt accounting/store/authenticated route tests, real worker tests
with controlled HTTP/HA boundaries, existing receipt UI regressions, and the actual
frontend inheritance chain in Chromium at 390px and 1440px. Browser tests cover
prefilled editing, barcode context, VAT confirmation, interrupted Add retry,
permanent discard, AI unavailability and the package weighing action. No live
household inventory, receipt images or configured AI provider is used by tests.
