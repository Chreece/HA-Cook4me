# v100: compact device header and joined menu controls

The header previously let the device status shrink next to several global
controls. On phones, long translated status text wrapped one character per line
and made the header several hundred pixels tall.

The shared layout now has:

- One compact top section: the animated device and its status on the left;
  language, a readable currency code, and one price-refresh icon on the right.
- Device selection and recipe-send targets on the device side when multiple
  Cook4Me devices are configured. Clicking the device still opens live details.
- One navigation row: the existing seven menu icons on the left and applicable
  filters on the right. Menus and long filter groups scroll horizontally on
  narrow screens, retaining 44-pixel controls.
- The selected menu's title and controls directly below that row, with one
  continuous surface. Today retains its date, clock and meal period; Search and
  Week retain their inputs and actions. Other views use the same heading area.
- Inactive filters still expand to the left of the filter toggle, and activated
  filters move to its right with positive selection counts.

The separate overview refresh is hidden from the top row. The price button uses
one `mdi:refresh` icon, retains its existing recipe-price action and busy state,
and no longer receives a second icon from the older decoration layer.

Navigation decoration now leaves already-ordered buttons in place. The previous
decoration repeatedly appended those buttons inside its own MutationObserver,
which could trip the existing DOM-loop guard. The guard remains enabled.

## Verification

`tests/frontend_v100_header_browser.mjs` loads the actual bundled panel, renders
all seven menus in English, German and Greek at 320, 390, 768 and 1600 pixels,
and checks header height, horizontal overflow, joined section placement, icon
counts, and filter placement. It also exercises actual menu clicks, filter
dialogs and migration, currency selection, saved interface language, one-click
price refresh, live device updates, device information and multiple-device send
targets. Both dark and light theme variables are checked, with the UI loop guard
active throughout. Calculator fixtures come from v99's real offline prices.

```sh
python tools/build_frontend_bundle_v100.py --check
node --check custom_components/cook4me/frontend/cook4me-panel-v100-bundle.js
node tests/frontend_v100_header_browser.mjs
python -m unittest discover -s tests -p test_deploy_offline_runtime_v100.py -v
```

For a non-default browser installation, set `COOK4ME_CHROMIUM_EXECUTABLE`.
Optional screenshots use `COOK4ME_SCREENSHOT_DIR`; the isolated browser test
supplies lightweight icon stand-ins for Home Assistant's `ha-icon` component.

The pinned v100 installer retains the previous integration, verifies staged
offline evidence and prices before stopping Home Assistant, and verifies the
installed bundle after restart. Activation failures restore the previous files.
Runtime build: `2026.9.17.4`. Price evidence and calculator behavior remain v99,
including confidence colours and explicit zero allowances. Live installation
must be run on the user's Home Assistant server.
