# Catalog cache transaction audit — v214

Continuation of the Cook4Me general bug hunt after v213.

## Ingredient catalog cache

The language-specific ingredient catalog cache was active in websocket v11 but
had two persistence risks:

- a language result was inserted into shared memory before Home Assistant
  storage accepted the write;
- first access created the cache without the common per-bridge load lock, so
  two simultaneous requests could construct and load two different cache
  objects.

Catalog writes now build a staged copy under a mutation lock, prune the staged
copy, persist it, and publish it only after storage succeeds. Concurrent language
writes therefore retain both language entries. The websocket accessor now uses
`store_load_lock`, so first access returns one canonical loaded cache instance.

## Recipe cache clear

Ordinary recipe-cache set/check operations intentionally use Home Assistant's
delayed Store save, preserving their existing cache semantics.

The explicit clear path is different: it performs an immediate awaited save.
Previously it cleared shared memory first, so a failed or cancelled immediate
save could make the cache appear empty until restart even though disk still held
the old entries.

Only the clear path now snapshots its prior state and restores it on any
exception/cancellation. Successful clears and delayed ordinary cache writes are
unchanged.

## Regression coverage

Production-class tests cover:
- failed/cancelled ingredient-catalog writes;
- concurrent language catalog writes;
- simultaneous websocket first access constructing one catalog cache;
- failed/cancelled recipe-cache bucket/full clear;
- successful recipe-cache clear;
- retained delayed-save behavior for ordinary recipe-cache set.

The General bug audit workflow now runs v208 through v214 regressions together
with the full current frontend browser suite. All other repository workflows
remain enabled.

No existing durable catalog or recipe-cache data is migrated or rewritten. No
live Home Assistant instance, network provider, inventory, camera, AI service,
scale or cooker was accessed.
