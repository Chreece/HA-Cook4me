# Unified product scanner and ingredient details (v80)

Your kitchen opens one fullscreen product capture window. Barcode, best-before,
nutrient-label and product-AI actions are four buttons beside a shared camera and
product form. With a live camera, a photo action captures the current frame;
without one, it opens the camera and asks the user to frame the package and press
again. Barcode scanning reads automatically, with a companion-app scanner or
manual barcode entry when browser detection is unavailable. Photo upload uses
the selected action. All manual fields, ingredient assignment, storage selection
and automatic/paid prices remain in the same window.

Scanned dates and nutrient values survive subsequent barcode lookup. Missing
barcode fields do not erase entered package details, and label nutrition takes
priority over generic barcode values. Saving still requires explicit confirmation,
a catalog ingredient and a storage place. Existing idempotent save/retry behavior
is retained. The old Ingredient stock – advanced entry section is removed from
the non-fullscreen Your kitchen page; existing stock editing and diet, storage,
price and integration settings remain available.

Ingredient clicks failed because the v31 endpoint awaited a v19 command decorated
with Home Assistant's `async_response`. That decorator schedules a task and returns
`None`; awaiting it raises `TypeError` and can emit an internal error before the
scheduled result arrives. Both registered endpoints now await an undecorated
shared async function. The regression tests reproduce HA's scheduling semantics
and verify exactly one result or error per request, including an unknown ingredient
and an unavailable device.

The active element is v80, with cache URL `2026.9.16.5`. The bundle includes the
unchanged earlier UI layers plus the new scanner layer. No firmware/device-control
changes are included.

Validation includes real Chromium desktop/mobile layouts, all four scan actions
with a generated camera stream and mocked recognition responses, manual entry,
stock/save retries, storage management, camera cleanup, stale results and a real
recipe-ingredient button opening its details. The existing automatic product and
recipe price checks run against v80. Physical camera recognition and deployment
still need the user's Home Assistant host.
