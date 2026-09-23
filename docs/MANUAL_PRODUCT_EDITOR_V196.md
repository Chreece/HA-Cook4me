# Manual product editor and next-action focus — v196

This change publishes the previously packaged v196 product editor on top of
`4ed38549c9277b999967f8b2566acc1f9cf6599e`. The production module, active-panel
wiring and 55 regression tests are identical to the tested local bundle.
The separate v189/v190 pricing bundles are not incorporated or replaced.
No live Home Assistant deployment is performed by this change.

## Barcode lookup

Search barcode sits next to the barcode input in manual additions and stock
package edits. Enter in that input runs lookup, not Save. Leading zeroes are
preserved; the existing 8/12/13/14-digit formats accept spaces and hyphens.
Invalid input remains visible with a field-specific message. Lookup uses the
existing authorized `cook4me/v33/barcode_lookup` route.

Found data fills missing product, brand, amount and nutrition fields and presents
all returned compatible ingredient suggestions. Explicit existing details remain:
selected ingredient mappings, remaining stock quantity, purchase price, expiry,
storage and container. Stock edits retain their lot ID and optimistic revision.
Unknown products and source failures do not clear the draft. A remembered barcode
mapping is retained; the first suggestion is not silently assigned. Different
nutrient bases are not combined.

## Save, Discard and validation

Discard and Save sit outside the camera/editor section at the lower right and
remain available while scrolling. Successful Save opens a clean manual form with
a new request ID, including after editing an existing package. Discard clears
only unsaved changes; it does not delete stored products. Product-specific fields
and assignments do not carry forward. Existing initial presets for unit, currency
and purchase date remain.

Failed validation retains the inputs, expands collapsed details, marks the first
invalid field in visual order, scrolls it into view and focuses it. Inline
messages are associated with the field. Checks cover amounts, units, mappings,
package count, barcode, dates, entered price/currency, edit price basis and
optional nutrient values/basis. Storage, barcode and expiry remain optional.
Unlimited stock retains its existing no-finite-package/no-package-price semantics.

Busy requests cannot be dismissed through the normal X path. Uncertain or
partially completed saves retain their frozen request and offer Retry save;
Discard cannot erase an uncertain transaction. Retries reuse the existing request
ID and backend idempotency mechanism. Authorization, validation, receipt privacy
and stock mutation handlers remain unchanged.

## Next-action focus

X or Escape with unsaved changes focuses the Keep editing / Discard confirmation.
Keep editing restores the previous editable field. Opening product, date or
nutrition details focuses the relevant input. Barcode lookup focuses the next
missing input or Save. Receipt item navigation and saved-draft selection also
move focus to the next required action, without clearing the receipt session.
Callbacks are guarded against stale products, closed dialogs and changed
users/entries. Ordinary redraws do not refocus inputs.

Receipt Apply retains its separate draft/request workflow and line-price basis.
The manual-reset footer is not shown for receipt sessions. Only pending product
receipt items can use barcode lookup. Incomplete receipt drafts remain saveable.
English, German and Greek editor strings are provided.

## Validation

The 55 Node tests passed again before publication using the production module
with controlled inherited UI/API boundaries. A dedicated Manual product editor
workflow runs those tests and checks the two frontend files' syntax. The existing
Validate, scanner compatibility, receipt and Greek regression workflows remain
in place; consult this pull request's checks for their results.

The original local bundle also recorded 16 Chromium scenario groups at 390x844
and 1366x900 and 10 guarded-applicator tests. Those are fixture-based tests, not
full-chain browser or live Home Assistant tests. Real barcode-provider, camera,
mobile-keyboard and live Home Assistant behavior remain untested.

Run the new and retained focused suites:

```sh
node --test tests/test_scanner_editor_v196.mjs
node --check custom_components/cook4me/frontend/scanner-editor-v196.js
node --check custom_components/cook4me/frontend/cook4me-panel-v180.js
python tests/test_receipts_v195.py
python tests/test_receipt_routes_v195.py
node --test tests/test_receipt_ui_v195.mjs
python tests/test_scanner_matching_v194.py
python tests/test_scanner_routes_v194.py
node --test tests/test_scanner_suggestions_v194.mjs
python -m unittest discover -s tests -p 'test_greek_catalog_audit_v19*.py'
```
