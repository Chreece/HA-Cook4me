# Recipe Hub and currency transaction audit — v212

Continuation of the general bug hunt after v211.

## Recipe Hub writes could publish data that storage rejected

Several central Recipe Hub mutations still changed shared memory first and then
awaited Home Assistant storage. A failed write could therefore leave the running
integration showing an unsaved dietary/profile change, stock change, pending
consumption, saved/deleted recipe, per-user UI preference or send-history entry.

These methods now build a complete copied hub snapshot, save that snapshot, and
publish it only after storage succeeds. Existing scanner/package operations that
already used this pattern remain unchanged.

## Pending consumption could be prepared from stale stock

The ingredient-deduction choices for a recipe were calculated before acquiring
the hub mutation lock. A concurrent inventory write could complete between that
calculation and the pending-consumption save, leaving the confirmation screen
based on an older stock snapshot.

The calculation now happens while holding the same lock as the snapshot that is
persisted.

## AI recipe safety could race a profile change

AI recipe dietary safety was checked before the Recipe Hub lock was acquired.
If the household/profile changed before the recipe was written, a recipe could
be saved even though it conflicted with the profile that ultimately coexisted
with it.

AI saves now re-check safety under the hub lock against the current profile
immediately before staging the recipe snapshot.

## Currency preference / rate writes

The currency store changed its in-memory preference/rate table before storage
and had no mutation lock. Failed writes could leave a non-durable selected
currency or ECB table visible. Initial auto-resolution could also race a manual
currency selection and overwrite it.

Preference initialization, explicit preference changes and rate refreshes now
share one lock, stage a copied store, persist first and then publish. Existing
cross-store behavior with the cost store remains unchanged; no attempt is made
to invent a distributed transaction between two Home Assistant Store files.

## Regression coverage

Production-method tests cover failed profile, inventory, pending-consumption,
confirmation, recipe, user-preference and send-history writes; concurrent recipe
saves; stock changing before pending-consumption preparation; and an AI save
waiting behind a profile change.

Currency tests cover failed initial preference, failed manual preference, failed
rate refresh and an initial auto-resolution racing a later explicit selection.

The General bug audit workflow runs all v208-v212 regressions plus the complete
current frontend browser suite. All other repository workflows remain enabled.

No existing durable data is migrated or rewritten. No live Home Assistant,
inventory, camera, AI provider, scale or cooker was accessed.
