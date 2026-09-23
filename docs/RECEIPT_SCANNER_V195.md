# Receipt scanner and streamlined weekly view — v195

## User workflow

Open My Kitchen → Camera / scanner. **Scan receipt** is available above the
scanner and in its camera mode controls. Frame the whole receipt and take a
photo, or use **Receipt photo** to choose an existing image. File upload remains
available without a camera; it does not automatically request camera access.
The existing configured image-capable Home Assistant AI Task is used, including
the HA default when no scanner-specific override is configured.

Recognition returns an editable receipt, not stock. Review the shop/place,
purchase date, currency and printed total. Unreadable or ambiguous values stay
empty. Original printed product wording is preserved beside the reviewed item.

The receipt list and previous/next buttons select an item. Horizontal swipes and
left/right keys also navigate outside form controls. Each item uses the current
scanner product editor, including all v194 compatible ingredient suggestions,
multiple ingredient links, full catalog search, package contents/count, storage,
container, purchase price, optional expiry and per-100-g/ml nutrition. Moving
between items retains edits. Date and nutrient photo scans enrich the current
item instead of starting a different receipt product.

**Save whole scan for later** persists every item, including incomplete entries,
and does not add inventory. **Saved receipts** reopens the user's saved drafts
across browser sessions and integration restarts. Nutrient values with an
unfinished basis survive draft saves; the basis must be confirmed before Apply.

**Discard this item** excludes one line without discarding its siblings.
**Discard whole scan** asks for confirmation and removes the saved draft only;
it does not undo products already added to stock. An uncertain submitted item
must be retried before the whole draft can be discarded.

**Apply this item to stock** is explicit. Catalog assignments, package amounts,
purchase date and any entered price/nutrition basis must be valid. After success,
the item becomes read-only and the next item opens. An interrupted save retains
its original request for retry, rather than adding another physical package.

## Weekly view

The weekly display no longer contains Reserved stock, Leftovers/remainings,
Product prices or Completed/successful purchases. Removal uses stable section
keys, not translated heading text. The weekly shopping delta, meal slots,
weekday options and totals remain. Underlying stock, price and purchase-history
data are not deleted; other views are unchanged.

## Price semantics

`lineTotal` is the amount paid for the entire printed line, across all packages.
`quantity` is the content of ONE package; `packageCount` is separate. Applying a
line costing EUR 3.98 for two 500-g packages passes amount=3.98 with basis=1000 g
to the existing price store. Each physical package uses that same total basis;
the price is prorated, not charged twice and not rounded prematurely per pack.

Product, discount, deposit and non-product lines remain distinguishable. A
basket-level discount is not silently allocated to a guessed product. Only
product-kind entries can become stock. The interface flags unknown amounts and
line sums that differ from the printed total. Review discounts and paid amounts
before applying. Unknown prices are blank, not zero; currencies are not converted.
Receipt estimates do not get copied into paid-price fields.

## Authorization, durability and limits

- Every route uses the existing integration/device authorization; drafts are
  additionally private to the authenticated HA user and integration entry.
- The AI Task must support images and be permitted for that user. Permissions are
  rechecked after waiting for the per-entry AI slot. Queue plus inference are
  limited to 90 seconds, one receipt inference at a time.
- Receipt image text is untrusted data. Output is allowlisted and bounded.
  Receipt recognition cannot infer nutrients, expiry, barcode or assignments.
- Photos use the existing JPEG validation and private temporary media-file path.
  Temporary local photos are removed after success or failure. Saved drafts do
  not contain images. The selected AI provider may process/retain data according
  to its own configuration and terms; this code cannot control that provider.
- Draft updates use optimistic revisions, preventing stale tabs from overwriting
  newer changes. Applying saves a durable immutable request before inventory
  writes and reuses the existing scanner's complete validation and save handler.
- Receipt stock retry records are persisted atomically with inventory separately
  from the ordinary 200-entry scanner retry cache. They are released after the
  owning draft is deleted. A hard 8192-record ceiling rejects new receipt items
  rather than evicting a retry record and risking duplicate stock.
- Maximum 120 lines per scan and 30 saved drafts per user/entry. Nothing is silently
  evicted. Scan unusually long receipts in separate sections.
- English, German and Greek receipt UI strings are included. No new runtime
  dependency, retailer scraper or separate AI credential is introduced.

## Validation

Local focused suites: **71 tests** (34 model/persistence, 15 route/ledger,
22 JavaScript session/review tests). They exercise production code with controlled
HA/AI/storage boundaries; they do not call a real AI provider or modify user stock.
The route tests cover ownership, permission revocation, schema/handler delegation,
photo cleanup, and durable retries after 250 unrelated ordinary scanner saves.

A local Chromium check loaded the complete existing v126→v180 panel chain plus
the new mixin with a controlled HA API. At a 390×844 viewport it verified editing,
previous/next retention, catalog selection, nutrient editing, save/reopen,
explicit Apply, read-only applied entries and per-item discard, without browser
JavaScript errors. This is not a real camera or live Home Assistant test.

Run:

```sh
python tests/test_receipts_v195.py
python tests/test_receipt_routes_v195.py
node --test tests/test_receipt_ui_v195.mjs
python tests/test_scanner_matching_v194.py
python tests/test_scanner_routes_v194.py
node --test tests/test_scanner_suggestions_v194.mjs
python -m unittest discover -s tests -p 'test_greek_catalog_audit_v19*.py'
```

The receipt workflow runs the new suites. Existing Validate, Greek audit and
scanner compatibility workflows remain unchanged. No live deployment is performed
by these code or test changes; install/update and restart the integration before
trying the new routes in Home Assistant.
