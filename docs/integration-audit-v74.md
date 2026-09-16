# Integration audit — v74

This update audits device startup/recovery/unload, recipe delivery and saved
collections, shared nutrition/cost/meal stores, progress, navigation and saved
preferences. It retains the v73 entity recovery and photo layout fixes.

## Runtime fixes

- Failed startup now returns promptly when the watcher exits and cleans up
  processes/tasks on failure or cancellation. Partial platform setup removes
  listeners and the failed bridge, allowing a clean retry.
- A watcher disconnect marks the device offline. Once setup has succeeded,
  subsequent watcher failures retry with backoff instead of permanently leaving
  stale online entities. A broken listener cannot stop updates to other entities.
- Reload/unload cancels device-owned metadata, queued-send and completion work.
  Cancelled client calls terminate and reap their subprocesses. Metadata fetches
  are bounded, and changing recipes cancels obsolete fetches, including returning
  to a cached recipe, leaving a recipe, or disconnecting. Process cleanup drains
  abandoned output pipes so a full buffer cannot delay shutdown after child exit.
- The final recipe step clears a stale next instruction. Consumption confirmation
  uses a snapshot of the finished recipe even if the device changes recipes while
  detail retrieval is pending.
- Device send commands share a lock. Deferred sends reserve work before loading
  storage, use the selected edition, and only clear the queue item they sent.
  Newer queued requests or cancellations survive older requests finishing/failing.
- Concurrent first access shares one loaded store for the recipe book, Today,
  weekly meals, meal history, nutrition, nutrition resolution, costs and currencies.
  Recipe-book writes are serialized and persist immutable snapshots.
- Work-queue reentrancy belongs to the owning task; inherited context in a new
  task cannot bypass serialization. Cancellation emits terminal progress, and
  late executor updates cannot reopen a completed progress notification.

## Dashboard fixes

Section refreshes preserve newer navigation choices and distinguish requests
for different users/devices. Loading indicators follow the selected device and
remain active until all overlapping refreshes for that section finish.
A failed preference save for an old device cannot
strand pending changes for the current device. An offline current device retains
pending preferences and waits for reconnect without a retry loop.

## Verification

`test_runtime_audit_v74.py` exercises the actual runtime functions, store factories
and a real cancelled Python child process, with HA/cloud I/O isolated.
`frontend_v74_async_navigation_smoke.mjs` reproduces the old navigation failure
against v73 and checks navigation and save races on the actual v74 bundle.
Additional cases reproduced the stale loading indicator and obsolete metadata
requests before fixing them. The existing catalog, recipe, announcement and
browser layout suites are also run.

The eleven historical nutrition-review test failures were traced to whole-ledger
counts being used for batch42–50 checkpoints after later explicit reviews. Those
tests now scope the historical checkpoint to the last review file for that batch,
as earlier batch tests already do. Exact source/fixture hashes and binding
validations remain in place; no nutrition data or review approvals are changed.

The pinned v74 installer runs runtime checks before replacing the integration,
keeps a backup, restarts HA and verifies the served dashboard bundle. Real cloud,
appliance and speaker behavior still requires verification on the user's host.
