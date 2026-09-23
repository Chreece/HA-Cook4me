# Compact device header and quiet non-device steps — v207

Recipe steps without a device operation no longer have a cooking-mode heading,
placeholder, preparation/serving chip, icon or reserved metadata spacing. The
instruction, numbering and active-step controls remain unchanged. Redecoration
also removes an earlier badge when program evidence is no longer present.

Real operation names still use the UI language. Multiple operations preserve
source order. An explicit but opaque program ID remains evidence of an operation;
its meaning is not guessed. The legacy evidence helper remains compatible while
`visibleStepCookingModes` filters its presentation-only manual/missing entries.

The upper device bar no longer builds the cooker photograph, model or simulated
screen. It shows the HA device name with one live-status icon and status text.
The registered user name takes precedence over the device's default name; the
config entry title is used only when no device name is available. Names are
escaped as text, truncated visually when long, and available in the tooltip.

The existing permission-checked device-state subscription supplies the name via
`state.deviceName`. No full device registry is sent to the browser. Registry name
changes for this device trigger a fresh authorized snapshot even without cooker
telemetry. Both listeners are removed on unsubscribe or permission loss; revoked
access clears the state/name. Registry reads stay on HA's event loop and use the
existing `(cook4me, device_uuid)` identifier. No HA devices are renamed.

Status uses the existing live-subscription view, not the old graphic's optimistic
phase fallback or queued-recipe guess. Offline, reconnecting, unavailable, ready,
preheating, cooking, pressure release, keep-warm, paused and finished remain
separate. A lost telemetry connection does not continue to show stale cooking.

The header uses HA theme variables and retains its language/currency controls,
device/target selection and device-information action. Click or Enter/Space opens
the existing information dialog; keyboard focus survives a telemetry redraw.
Multi-device selectors and pending-delivery notifications are not removed. The
normal bar is compact, with wrapping/truncation rather than off-screen controls
on phones. The navigation-hover fix and prior app-wide styling remain intact.

## Validation and delivery

Before publication: 24 Node cases, 9 tests of production snapshot/subscription
functions and 68 Chromium assertions against production status/header code with
a controlled shell passed, across 360, 390, 844 and 1440 pixel widths. The step
renderer also passed 39 retained/updated browser assertions. Tests for the missing
header module and missing HA name failed before implementation.

The existing recipe-step workflow runs those cases and the new browser suite
against the complete current frontend. Its older browser expectations now count
five device-operation rows, not the sixth preparation row, and explicitly assert
that preparation has no label. Existing evidence/localization tests are retained.
No test is removed or skipped.

Changed original files were verified against current main blob hashes before
editing; publication applies only the explicit delta over backend v206, not the
retained bootstrap checkout/catalog. Runtime URL, query and active component
advance to v207. Manifest, catalog, recipe selection, pricing, inventory, cooker
transport and HACS archive rules are unchanged. No live HA deployment or cooker
action is performed.

HA device-registry properties and registry event contract were checked against
https://developers.home-assistant.io/docs/device_registry_index/ and the official
Home Assistant core device registry source.
