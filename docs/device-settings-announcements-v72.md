# Device settings and announcements (v72)

Click the Cook4Me status header to open device settings. Home Assistant's device
page also has a Visit link to this panel, with the correct appliance selected.
Settings belong to the signed-in HA user and selected appliance, and are stored
on the HA server so they follow the user between browsers and mobile apps.

## Consolidated entities

The default device exposes State and Connected. State keeps the recipe, step,
full instruction, program, phase, status, timing, progress and firmware as
attributes. Connected also contains connection timestamps, firmware and update
status. An offline device now reports offline rather than a stale cooking phase.

Existing duplicate sensors and Updating are disabled by a one-time migration.
Their registry entries are retained, so they can be re-enabled for automations
that use the old entity IDs. Such manual re-enablement is respected on subsequent
restarts. Automations using a disabled legacy sensor should instead use State
attributes or re-enable that sensor. No recipes, history or user profiles are
changed by this migration.

## Announcements

Speech starts disabled. Each user can configure:

- Recipe loading confirmed by the device, current step, cooking phase changes,
  and optionally connection changes during cooking.
- Multiple available media players with audio playback. Players with HA's
  announcement capability are marked ↩; others may interrupt current playback.
- A TTS entity, one of its supported output languages, and a voice where the
  provider advertises voices for that language.
- An optional available AI Task entity for translating the complete spoken
  message before TTS. The selected entity is used explicitly; there is no
  automatic fallback to another AI service.

Save persists the choices. Test saves them first, then speaks a sample on the
selected players. Enabling requires valid speakers, TTS and language selections.
An unavailable configuration can still be disabled. Without AI, recipe title and
instruction text stay in their original language. Fixed state phrases are
authored in English, Greek, German and French, with English fallback. Selecting
AI also translates those phrases to the requested output language.

Announcements use `tts.speak`, which requests announcement playback through HA.
The speech call carries the owning user's context. Device, AI, TTS and player
permissions are checked; permissions and saved preferences are rechecked after
AI completes. Each user's settings and progress subscriptions are private.
The existing bottom-right popup displays translation, speech and errors.

Startup snapshots, reconnect replays and timer/progress ticks do not repeat
steps. Delayed recipe metadata can announce the new step once its text arrives.
Queued recipes are announced only when confirmed loaded by the device. Stale
steps are discarded after a slow AI response. AI failures or changed numeric
quantities skip speech and report an error. Identical announcements to a shared
speaker are sent once per event, even when multiple users select it. Pending
background work is bounded, expires after 90 seconds, and is cancelled on unload.

## Verification

The focused Python suite exercises real event tracking, settings persistence,
entity migration, delivery, permission changes, AI failures, stale-step
discarding, cleanup and websocket user isolation with HA I/O replaced by test
doubles. DOM checks exercise the settings UI, language/voice selection, multiple
speakers, test action, account/device changes, private progress and deep linking.
Existing recipe-card and catalog suites run against the new bundle. Installer
checks cover source pinning, preflight failures, backup and rollback.

Live speaker playback and appliance behavior require verification on the user's
HA host, which is not reachable from the development workspace. No real speaker
is contacted during tests. DOM tests do not provide a pixel-level visual check.

API references: [HA TTS](https://www.home-assistant.io/integrations/tts/),
[media player features](https://developers.home-assistant.io/docs/core/entity/media-player/),
[TTS entity implementation](https://github.com/home-assistant/core/blob/dev/homeassistant/components/tts/entity.py).
