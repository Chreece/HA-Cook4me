# General bug audit — v208

Audited against `a48e5a3b5b130271b9e43b4640fb3f2d7f961978` (v207).
This batch fixes reproduced state races and data-integrity failures, not a
cosmetic refresh. It does not claim the entire integration is bug-free.

## 1. Filters can revert while a save is pending

Returning to the page or reconnecting fetches saved preferences. The restore
used only the queued patch, ignoring the in-flight write which had already
cleared that queue. Older server filters and even the old active view could
replace the user's just-selected settings. An acknowledgement arriving before
the older read completed had the same problem.

Restore now retains the pending patch at read start and merges it with the
latest in-flight/queued patches. Latest edits still win, separate views remain
separate, and unrelated remote views can refresh. An abandoned connection's
read no longer blocks the new connection's restore or marks it as loaded.

## 2. Late package details can open or overwrite the wrong editor

Two package clicks returning in reverse order let the older response overwrite
the newer edit target. A pending lookup could also force-close a newly opened
manual form or reopen an editor after navigation. Late errors could appear
under a different user or view.

The active product-editor mixin now owns guarded package opening. Only the
latest request in the same user/entry/view can open a form. Existing dialogs,
replaced drafts and edits typed during opening are preserved. The lot ID,
remaining quantity, optimistic version and first-field focus remain intact.
Closed old-context busy flags do not prevent a fresh editor. The inactive v112
source and its compiled historical bundle are not patched independently.

## 3. Remaining stock can incorrectly become a barcode's retail package size

Editing a 500 g product with 125 g remaining wrote 125 g into the remembered
barcode mapping. The next lookup relying on that mapping could suggest the
wrong package quantity. Converting pantry stock to unlimited also erased the
known finite retail size.

Those operations now update reviewed metadata and ingredient assignments while
preserving the existing package quantity/unit together, under the mapping
store's existing write lock. If no original size is known, it remains unknown;
remaining stock is never used to invent one. A newly reviewed measured product
scan can still set or correct package size. No stored mappings are bulk-fixed
because their original sizes cannot be reconstructed reliably.

## 4. Failed label writes expose unsaved nutrition in memory

The label saver modified its shared in-memory data before awaiting disk. A
failure or cancelled waiter could leave readers seeing the unconfirmed label.

New data is staged and published only after the storage call succeeds. Failed
writes retain the prior in-memory state; retry still replaces the same exact
lot rather than adding another. Existing package-label replacement takes the
staged result forward, and explicit label removal remains supported. This does
not assert that an interrupted external write can never reach disk; existing
review/retry protections remain responsible for uncertain completion.

## Validation and scope

New controlled tests execute production functions/classes, replacing only HA,
DOM or storage service boundaries. Initial tests reproduced filter/editor races
and failed-write/package-size errors before implementation. Tests also cover
successful saves, optional data, scope changes, unchanged source records,
unit-pair preservation and retries. The new General bug audit workflow runs the
Python and Node suites plus the complete current frontend at phone portrait,
phone landscape and desktop sizes. All existing workflows remain enabled.

Local bootstrap is the retained repository backup. Every edited pre-existing
file was hash-verified against current main; only the explicit changed-file
delta is published over v207. Full current frontend/catalog validation is
performed by PR CI, not inferred from the older local bootstrap.

Runtime path, query and active element advance together to v208. All existing
meal eligibility, day grouping, cooking-mode labels, compact header, price
market/language rules, stock allocation, scanner controls and archive exclusions
remain on the current base. No real user stock, HA configuration, camera, AI
provider or cooker was accessed or altered. No live deployment is performed.

```sh
python tests/test_general_audit_v208.py
node --test tests/test_general_audit_v208.mjs
python tests/browser_general_audit_v208.py
```
