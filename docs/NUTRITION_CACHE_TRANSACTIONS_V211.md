# Nutrition and derived-cost persistence audit — v211

Continuation of the Cook4Me general bug hunt after v210.

## Nutrition store rollback

The nutrition store already serialized mutations, but several legacy methods
still edited `store._data` before awaiting Home Assistant storage. A failed or
cancelled write could therefore leave generic nutrient profiles or exact product
lot quantities changed only in memory.

The shared nutrition mutation guard now snapshots the last published state before
running a mutation and restores it on any exception or cancellation. This covers
generic nutrition, exact stock-lot records, reconciliation and confirmed
consumption, while remaining compatible with the newer staged label/package
writers introduced in v208.

The nutrition store also passes a deep copy to Home Assistant storage so a slow
serializer cannot observe later in-memory mutations through the same object.

## Recipe-cost cache durability

The persistent recipe-cost cache inserted a calculated entry into its in-memory
cache before the storage write succeeded. If storage failed, the next recipe
price request could become a cache hit on data which was never persisted.

Cost-cache misses now build a staged cache copy, save that copy, and only then
publish it in memory. A failed or cancelled write leaves the old cache intact.
The existing cache lock still serializes simultaneous recipe calculations, so
different keys are retained rather than racing.

This is derived pricing data only; no price evidence, paid prices or supermarket
settings are changed.

## Regression coverage

New production-class tests cover:
- failed/cancelled generic nutrition writes,
- failed exact-product lot writes,
- failed reconcile and consumption updates,
- concurrent nutrition mutations,
- failed/cancelled recipe-cost cache writes,
- successful retry becoming a genuine cache hit,
- concurrent cache misses retaining both keys.

The General bug audit workflow now runs v208 through v211 regressions together
with the complete current frontend browser checks. All other repository workflows
remain enabled.

No existing durable nutrition data or cost evidence is migrated or rewritten.
No live Home Assistant instance, user stock, camera, AI provider, scale or cooker
was accessed.
