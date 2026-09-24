# Recipe Hub transaction audit — v212

Continuation of the Cook4Me general bug hunt after v211.

## Reproduced failure window

The central Recipe Hub store already serialized mutations with one lock, but a
number of methods still changed `self._data` before awaiting Home Assistant
storage. If that write failed or the task was cancelled, the running process
could expose data that had never been durably saved.

Affected in-place paths include:
- profile and household preference updates;
- inventory add/update/remove;
- pending consumption creation/confirmation/revision/clear;
- per-user and global UI preferences;
- saved recipe create/update/delete;
- sent-recipe history used for ranking habits.

The scanner/package paths which already stage a copied data tree and publish only
after persistence remain on their existing implementation.

## Fix

A Recipe Hub durable-mutation context now wraps only the in-place paths. It:
1. acquires the existing Recipe Hub mutation lock;
2. snapshots the currently published data after the lock is acquired;
3. runs the existing mutation unchanged;
4. restores the snapshot on any exception or cancellation.

The ordinary Recipe Hub save also writes a deep copy to Home Assistant storage,
so a slow serializer cannot observe later in-memory edits through the same object.

Because the snapshot is taken only after acquiring the existing lock, a failed
second mutation cannot roll back a successful first mutation which completed
while it was waiting.

## Regression coverage

Production-method regressions cover:
- failed profile and inventory writes;
- failed pending-consumption creation and confirmation;
- failed per-user and global UI preference writes;
- failed saved-recipe create/delete;
- failed sent-recipe history writes;
- cancellation during an in-flight UI preference write;
- concurrent mutations preserving both successful changes;
- a failed later mutation retaining an earlier durable success;
- the already-staged storage-location path remaining intact.

The General bug audit workflow now runs v208 through v212 regressions together
with the complete current frontend browser checks. All other repository workflows
remain enabled.

No existing durable profile, inventory, recipe, preference or history record is
migrated or rewritten. No live Home Assistant instance, user inventory, camera,
AI provider, scale or cooker was accessed.
