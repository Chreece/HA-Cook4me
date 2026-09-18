# Product entry, device information and announcements (v81)

Your kitchen has one **Add product** button. It opens the existing fullscreen
capture window with the four scanning actions and manual fields. The duplicate
header shortcut and separate manual-add button are removed.

**Your kitchen → Integration settings → Device options → Announcements** now
contains the existing per-account, per-device speech preferences: speakers, TTS,
language, voice, translation, event switches, save and test. Device state and
firmware are removed from that form. Clicking the device header, using its
keyboard controls, or following Home Assistant's device-page link instead opens
a device-information dialog with firmware, connection and reported cooking data.

A small Cook4Me illustration displays the current state in both the header and
information dialog. Preheating pulses, cooking emits steam, pressure release has
faster steam, and keeping warm uses gentler steam. Preparation opens the lid;
ready/finished displays a check mark. Firmware updates show a rotating indicator.
Offline, stopped, paused and unknown states remain static with explicit text.
Reduced-motion preferences disable animation while preserving all labels.

The new `cook4me/v32/device_state_subscribe` command sends the initial bridge
snapshot and subsequent listener updates. It makes no polling or cloud requests.
It requires read permission on the selected device, exposes only allowlisted
telemetry and checks access on every update. Revocation clears the displayed
state and removes the listener. Read-only users need no control permission to
view telemetry; announcement settings retain their existing control checks.

The UI unsubscribes on device, user and connection changes or removal. Late
callbacks are ignored. A lost HA connection stops animations, a device disconnect
shows offline even if the last phase said cooking, and unknown phases are never
presented as active cooking. Live telemetry takes precedence over a late overview
response. Time remaining is the latest reported duration, not an extrapolated
countdown. English, German and Greek labels are included.

Active panel: `cook4me-recipe-hub-panel-v81`; cache URL: `2026.9.16.6`.
No cooker commands, firmware writes or live household/device tests were performed.

## Validation and delivery

- Real Chromium checks pass for the single product button, fullscreen manual and
  scan fields, all illustrated states, live updates in both locations, late
  overview results, disconnect/reconnect, keyboard opening/Escape, reduced motion,
  account/device changes and the device-page deep link. Mobile information dialogs
  fit at 360 px in English, German and Greek; screenshots were inspected.
- The existing unified-scanner/ingredient-click browser suite and automatic
  product/recipe pricing suite pass against v81. Recognition and telemetry in
  browser tests use controlled responses, not a physical device.
- Five new backend tests cover initial telemetry, updates, allowlisted payloads,
  read-only access, denied/inactive users, revoked permissions and cleanup.
- All 14 existing announcement backend tests pass.
- All four v81 pinned-installer tests pass, including backup/install, invalid config
  mounts, missing source data and automatic rollback after activation failure.
- Bundle, JavaScript/Python syntax, version, workflow parsing and diff checks pass.

Runtime commit: `feaf043f429b812221db4d2c5a5033519b5f9c11`.
Pinned installer: `tools/deploy_offline_runtime_v81.sh`.

The complete Python regression suite passed: **1,436 tests** (296.747 seconds),
including the new telemetry and pinned-installer checks.
