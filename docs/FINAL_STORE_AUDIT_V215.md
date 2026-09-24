# Final persistent-store audit — v215

This batch completes the source sweep of every direct Home Assistant `Store`
usage under `custom_components/cook4me`.

## One catalog store, one writer

Two active ingredient-catalog implementations were writing the exact same
storage key:

- the canonical v11 `Cook4MeIngredientCatalogCache`;
- websocket v28's private `Store(...ingredient_catalog)` plus separate in-memory
  dictionary.

They used different metadata schemas. v11 expected `timestamp`; v28 wrote
`checkedAt/updatedAt`. A v28-written row could therefore be treated by v11 as
timestamp zero and pruned, while independent in-memory writers could overwrite
one another.

v28 now reuses `v11._cache(bridge)` directly. There is no second Store object
or second in-memory catalog tree.

The canonical cache accepts both historical schemas:
- legacy v11 `timestamp` rows;
- legacy v28 `checkedAt/updatedAt` rows.

Reads expose normalized `timestamp`, `checkedAt` and `updatedAt` metadata.
A successful unchanged online check advances its check/timestamp while retaining
the previous update time; changed content advances update time. Existing durable
rows are read in place and are not bulk rewritten.

## Nutrition-resolution negative cache

The last direct persistent store not already transaction-audited was the
nutrition-resolution negative cache. Failure records, clears and transient clears
mutated shared memory before storage and had no mutation lock.

Those operations now stage a copied failure map under one lock, persist first,
then publish. Failed/cancelled writes leave the previously durable negative-cache
state visible, and concurrent failures retain both identities.

## Recipe cache note

The v214 audit already fixed the immediate recipe-cache clear path. Ordinary
recipe cache set/check operations intentionally keep Home Assistant Store's
delayed-save semantics and are not converted to synchronous writes.

## Coverage

New production-class regressions verify:
- loading a historical v28 catalog row with no timestamp;
- loading a historical v11 row with no checkedAt/updatedAt;
- unchanged versus changed catalog update-time semantics;
- v28 contains no second Home Assistant Store writer;
- v28 reads/writes the exact canonical v11 cache object;
- failed/cancelled nutrition-resolution writes;
- failed clear rollback;
- concurrent resolution failures preserving both records.

With this batch, every direct Home Assistant `Store` instance in Cook4Me has
been inspected for first-load, failed-write and concurrent-mutation behavior.
Caches with deliberate delayed-save semantics remain deliberately asynchronous.

All prior v208-v214 regression suites remain in the General bug audit workflow,
and all other repository workflows remain enabled.

No existing durable catalog, nutrition failure, inventory, recipe or user setting
is migrated or rewritten. No live Home Assistant instance, provider, camera,
AI service, scale or cooker was accessed.
