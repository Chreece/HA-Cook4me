# Lifecycle transaction audit — v210

Continuation of the Cook4Me general bug hunt after v209.

The weekly/leftover lifecycle store persisted several user-visible structures:
weekly slots, selection state, leftovers, recipe feedback, meal costs and approved
substitutions. Those methods changed the shared in-memory state first and only
then awaited Home Assistant storage. If the write failed or the task was
cancelled, the current process could continue with a state that was never
durably saved.

## Central transaction guard

All lifecycle mutations now run under one persistence mutation lock. The guard:

1. snapshots the last published in-memory state;
2. runs exactly one existing mutation method;
3. lets the existing storage write complete while no other lifecycle mutation
   can interleave;
4. restores the snapshot on any exception or cancellation.

The original mutation methods, meal planning rules, leftover calculations,
feedback schema and substitution logic are otherwise unchanged. Storage receives
a deep copy so an asynchronous persistence implementation cannot observe later
in-memory mutations through the same object reference.

The existing weekly-generation lock remains separate. A generator can hold the
weekly lock and call a durable lifecycle mutation normally; the two locks do not
recursively acquire each other.

## Covered failure paths

Regression tests cover failed weekly-plan replacement, failed selected-slot
updates, failed leftover consumption and reweighing, failed feedback, meal-cost
and substitution writes, plus cancellation during an in-flight save. Every case
must leave the previously durable in-memory state unchanged.

Concurrency tests delay the first storage write and start a second mutation.
The second caller must wait, and the final durable state must contain both slot
updates / unrelated leftover and feedback changes rather than whichever write
happened to finish last.

Successful leftover-by-weight and settings writes are also checked to make sure
normal behavior and persisted values remain unchanged.

## Scope

This is a backend persistence fix. No frontend runtime rotation is required and
no existing durable meal plan, leftover, feedback, substitution or cost record
is migrated or rewritten.

The extended General bug audit workflow runs v208, v209 and v210 regressions
together with the complete current frontend browser tests. All other repository
workflows remain enabled.

No live Home Assistant data, inventory, camera, AI provider, scale or cooker was
accessed.
