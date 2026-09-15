# Recipe photo bounds and entity recovery (v73)

## Device entity recovery

The v72 device settings link used a relative configuration URL. Home Assistant
validates the URL while registering each entity's device and rejects a missing
scheme or host. This prevented State and Connected from loading after the older
duplicate sensors had been disabled. The link now uses
`homeassistant://cook4me?device=<entry_id>`, preserving the device settings route
with a supported scheme and host. Existing primary entity IDs are unchanged.

The one-time consolidation now runs after the entity platforms finish loading.
It disables duplicate sensors only when both primary entities have live states;
restored, unknown or unavailable states do not qualify. Offline/off states do,
because a disconnected appliance can still have successfully loaded entities.
If either entity fails setup, existing legacy sensors remain enabled and the
migration can retry on the next setup. Previous consolidation and explicit user
enable/disable choices are preserved.

Two setup regression checks cover the URL contract, primary entity defaults and
values, and setup order. Two migration checks cover failed and restored entities.
The installer runs these checks before changing the installed integration.
The registry contract is documented in Home Assistant's
[device registry source](https://github.com/home-assistant/core/blob/2026.9.0/homeassistant/helpers/device_registry.py).

## Photo bounds

The fixed 310 px recipe card contains an 88 px title and 220 px photo, plus
two 1 px borders. Older styles could still add 16 px padding and a 10 px flex
gap, pushing the photo and bottom action controls outside the clipped card.
The duplicate padding rules had equal specificity and depended on when the
older stylesheet was inserted.

The shared card now explicitly clears outer padding and gaps with a more
specific selector. The media and photo wrappers have consistent box sizing
and no additional margin or padding. The existing card dimensions, responsive
widths, image fit, centered translucent buttons and fullscreen behavior remain.
Unusually crowded action areas can scroll within the photo instead of escaping
its bounds. Expanded cards continue to show their details in a scrollable body.

The new Playwright regression uses the actual panel bundle and browser layout.
It deliberately inserts the old stylesheet last, reproduces clipping with v72,
and verifies the repaired layout at 1800, 1160, 900 and 390 px viewport widths.
It checks photo and button rectangles in weekly, regular and expanded cards,
including missing photos and multiple Cook4Me targets. The 42 checked cards
retain their intended dimensions and no longer clip their photo area or buttons.

Run with `node tests/frontend_v73_photo_bounds_browser.mjs` after installing
Playwright's Chromium. `COOK4ME_CHROMIUM_EXECUTABLE` can select an existing
Chromium executable, and `COOK4ME_TEST_PANEL_VERSION=72` reproduces the regression.
