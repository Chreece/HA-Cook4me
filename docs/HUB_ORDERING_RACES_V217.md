# Recipe Hub ordering race audit — v217

Continuation of the Cook4Me general bug hunt after v216.

During cleanup of an older superseded v212 branch, two ordering fixes were found
that were not yet represented in current main. The old branch itself is not
merged because its persistence implementation has since been superseded by
v212/v213; only the still-relevant race fixes are carried forward here.

## Pending consumption vs. inventory edits

Pending consumption choices were calculated before acquiring the Recipe Hub
mutation lock. If a stock edit was already in progress, the calculation could
observe that edit's transient in-memory state. If the stock write then failed and
rolled back, the pending confirmation could still be saved using the stock that
never became durable.

Pending-consumption calculation now happens inside the same durable-mutation
context as the saved pending record. It therefore sees the inventory state that
actually wins lock ordering and coexists with the pending confirmation.

## AI recipe safety vs. profile changes

AI recipe safety was checked before acquiring the Recipe Hub mutation lock. A
profile update already waiting ahead of the AI save could commit first, while
the AI recipe was still saved using a safety decision made against the previous
profile.

Normalization remains outside the lock, but the dietary safety check now runs
inside the durable mutation after lock acquisition and before changing the saved
recipe list. The recipe is therefore validated against the profile it will
coexist with.

## Regression coverage

The production Recipe Hub transaction suite now adds two ordering tests:

- a stock update mutates its transaction state, blocks on storage, then fails;
  a concurrently requested pending-consumption record must wait and use the
  rolled-back durable inventory rather than the transient quantity;
- a profile change is queued before an AI recipe save behind the same lock; the
  profile becomes vegan first and the AI recipe must be rejected by the safety
  check performed after lock acquisition.

All existing v208-v216 persistent-state and full-current-frontend regressions
remain enabled.

Backend-only v217. No stored inventory, recipe, profile or pending-consumption
record is migrated or rewritten. No live Home Assistant instance or cooker was
accessed.
