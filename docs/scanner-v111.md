# Continuous product scanner — v111

Panel build: `2026.9.17.15`.

The product scanner keeps the same camera stream and video element through form
refreshes, barcode lookup, label capture, ingredient selection and Apply. Closing
or stopping the camera still releases the device. Late camera permissions and
recognition responses are discarded when the session has ended or changed.

Barcode, best-before, nutrition and AI product modes have icon controls and
framing guides inside the camera. The barcode mode automatically looks up a
recognized code, showing a spinner followed by a green tick, product name,
quantity/unit, storage location and Apply. Unrecognized products have an explicit
message. Tapping the image resumes scanning; controls remain interactive.

Best-before and nutrition scans attach their results to the current recognized
product and display them in the camera. Scanned and manually edited nutrition
is preserved when looking up the same barcode again. A new product gets a fresh
draft and request ID, without inheriting expiry or nutrition from the previous
product. Apply adds the reviewed product to stock; retry after an uncertain save
uses exactly the same request and quantity, preventing duplicate additions.

Matching searches names and reviewed aliases from every language in the offline
ingredient catalog, preserving the ingredient identity and current UI label.
Unambiguous strong matches fill the ingredient automatically; tied or weak
matches remain suggestions. Saved barcode mappings are resolved back to the
current catalog. The manual picker now contains the complete available food
catalog, with stable IDs for ingredients without a legacy key, searchable across
language aliases. The previous 150-item cap is removed. Catalog counts depend
on locale grouping: this build has 2,948 Greek picker rows, 3,680 English rows
and 4,069 German rows.

Automatic barcode decoding uses the browser's BarcodeDetector when available.
The live camera remains available if that API is absent, with typed barcode and
companion-app alternatives. Photo barcode decoding also requires BarcodeDetector.
Date, nutrition and AI product recognition use the configured Home Assistant AI
photo provider. Ingredient matching itself uses the bundled offline catalog.

Validation:

- Seven backend tests cover real catalog aliases in multiple scripts, stable
  IDs, the complete localized picker, conservative matching, learned mappings,
  review-only lookup and saving a keyless ingredient.
- Browser checks use the actual bundled panel with a synthetic camera stream
  and mocked product/AI responses. They cover continuous capture, status states,
  label-to-product association, quantity/storage controls, immutable save retry,
  new-product isolation, stale responses, missing barcode support, late camera permissions and responsive
  English/German/Greek layouts.
- Existing barcode/product capture tests and weekly-plan/header browser checks
  guard the surrounding flows. Installer tests cover staged validation, backups,
  activation and rollback.

No live Home Assistant host, phone camera, barcode provider or AI provider was
available for end-to-end hardware verification in this environment.

Published runtime commit: `5c53f8b7299d1692b8a461cd7d642dcae038fc26`.

Verified runtime tree: `68be73b8cbced170cbba8635ffd690d04f1a54e4`.
