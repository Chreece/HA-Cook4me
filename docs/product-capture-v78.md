# Product capture and kitchen settings (v78)

The profile section is now **Your kitchen**, with separate Stock & products,
Food preferences, Storage places and Integration settings menus. Existing diet,
allergy, avoided-food, household, nutrition-provider and device/announcement
settings remain available outside capture. The older ingredient-level entry is
retained under Advanced entry, including unlimited stock.

**Scan a product** opens a fullscreen dialog with Barcode, Best before,
Nutrition label, Product · AI and Add manually modes. These modes share one draft.
A barcode lookup never adds stock, including known or confidently matched products.
Users review product/package details, select a Cook4Me catalog ingredient and
choose a storage place before **Confirm & add to stock**. Dates and nutrition
can be typed manually. Blank nutrients remain unknown; explicit zero is preserved.

Named storage places have stable IDs, a name and a fridge/freezer/pantry/other
category. Renaming a place keeps existing stock linked. Its category remains
available to existing inventory logic. A place containing stock cannot be deleted;
move its lots using the stock editor first. Existing category-only lots are kept.

Photo recognition uses an available Home Assistant AI Task with data-generation
and image-attachment support, selected under Integration settings. The preferred
HA AI Task is used when no explicit choice is set. A configured HA media directory
is required. The browser resizes/re-encodes photos as JPEG; the server validates
size/content and provides a random temporary media attachment, removed on success
or failure. Photos go to that configured AI provider. Product recognition does
not infer nutrition or expiry; date/label modes transcribe visible information into
the draft. The user reviews every result. Manual entry and barcode lookup do not
require AI.

Implementation follows Home Assistant's [AI Task API](https://developers.home-assistant.io/docs/core/entity/ai-task/)
and [generate-data attachment format](https://www.home-assistant.io/actions/ai_task.generate_data/).
Browser live barcode capture uses BarcodeDetector, with companion-app scanning
where available and typed barcode entry as fallback.

Saving validates the ingredient against the real catalog and rechecks the chosen
storage place under the inventory lock. An immutable request ID and receipt are
saved with stock in one transaction, so a lost response or partial nutrition-save
failure can be retried without adding another lot. The last 200 receipts survive
restarts. Unknown save outcomes retain the original request for retry; validation
failures allow correction. Unlimited ingredients must be changed to measured
stock before individual packages can be added. Write failures cannot leave the new
stock or storage-place mutation committed only in memory.

The camera stops on close, mode changes, backgrounding, navigation, account/device
changes and disconnect. Permission requests resolving after closure stop their
streams. Late lookup or AI responses cannot populate a newer capture session.
The dialog uses the browser's modal top layer with phone safe-area support; closing
an edited unsaved draft asks whether to discard it.

Validation is recorded with the installer delivery. No live HA deployment or real
provider image recognition was performed in this workspace.

## Validation and delivery

- Full Python suite: **1,392 tests passed** (255.730 seconds), including 18 new
  capture/storage regressions and the retained device-observer tests.
- Chromium: fullscreen geometry at 1280, 390 and 360 px; manual save; barcode
  preview without stock mutation; date/nutrition draft merging; explicit zeros;
  duplicate retry payloads; location create/rename/delete; stock-lot editing;
  camera permission cleanup; stale results; draft discard; preserved preferences;
  and English/German/Greek mobile layouts.
- Active v78 retains passing dietary substitution, original-program Send,
  device-settings and asynchronous-navigation checks.
- Bundle consistency, Python/JavaScript syntax, version and diff checks passed.
- The pinned installer is tested separately for successful replacement/backup,
  missing locale, wrong config mount and rollback after failed activation.

Runtime commit: `0b0e3fcd0c8fd00b38d6b8fd5a0b63b6fb2f2138`.
Installer: `tools/deploy_offline_runtime_v78.sh`.
The existing draft PR #152 is updated; it is not merged. Installation still runs
on the HA host using the supplied command, with preflight, backup and rollback.
