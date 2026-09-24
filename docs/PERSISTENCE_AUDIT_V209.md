# Persistence bug audit — v209

Continuation of the v208 general bug hunt, based on main
`9e6a1912a7418c920f6dd88fb10fc8db295a8a03`.

This batch is limited to reproduced persistence/concurrency failures. It does not
claim the integration is free of other bugs.

## Today plan cache could publish an unsaved plan

`Cook4MeTodayPlanStore.async_set()` replaced the in-memory Today snapshot before
awaiting Home Assistant storage. A failed disk write therefore left the current
process showing a plan that would disappear after restart. A failed clear had the
same problem in reverse.

Writes and clears are now serialized. A new snapshot becomes visible only after
its save/remove succeeds. Overlapping generations commit in call order, so an
older delayed write cannot finish after and replace the later Today result.

## Meal history could survive a failed write only in memory

Recording or editing a meal mutated `_data` before storage. This is especially
dangerous for history edits because the websocket layer compensates inventory
when history persistence fails; before this fix the inventory could be rolled
back while the edited meal still remained visible in memory.

Meal records and edits are now staged under a mutation lock and published only
after the storage write succeeds. Concurrent meal records are serialized and
both remain in the final durable history.

## Smart-scale settings/sessions had the same write-through failure

Selected scale, containers, recipe ingredient measurements, batch weight and
session removal all changed shared memory before persistence. Storage failure
could therefore make the UI report a selection/container/measurement that was
not durable, or hide a session whose deletion failed.

All smart-scale mutations now use a staged copy under one lock and publish only
after persistence. Concurrent container and measurement writes are merged in
serialized call order rather than racing on the shared object.

## Smart-scale first-load race

Unlike other Cook4Me stores, `smart_scale_store_for_bridge()` did not use the
per-bridge load lock. Two simultaneous websocket requests on first access could
create and load two different store objects; whichever assigned the bridge last
became canonical, while the other caller could write into the abandoned object.

Smart scale now uses the same `store_load_lock` pattern as Today, meal history,
receipt and other stores. Concurrent first access returns one loaded instance.

## Boundaries

No stock amounts, meal records, scale sessions or Today plans are migrated or
rewritten by this change. Existing durable data remains unchanged. The change
only alters when new in-memory state is published and serializes overlapping
writes.

This is backend/store behavior only, so no frontend runtime rotation is required.

The extended General bug audit workflow covers failure, cancellation-style
failed writes, concurrent writes, first-load serialization and retained v208
regressions. All existing repository workflows remain enabled.

No live Home Assistant storage, user inventory, scale, camera, AI provider or
cooker was accessed.
