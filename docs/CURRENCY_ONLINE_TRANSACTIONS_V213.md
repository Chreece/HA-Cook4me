# Currency and online-cache transaction audit — v213

Continuation of the Cook4Me general bug hunt after v212.

## Online cache

The persistent online cache already serialized record writes, but it modified
`_rows` before awaiting Home Assistant storage. A failed or cancelled save
could therefore make the current process use a provider result or failure
timestamp that had never been persisted. Two first-time callers could also
create two separate cache objects because its bridge accessor lacked the common
per-store load lock.

The cache now snapshots its published rows inside the existing write lock and
restores them on any exception/cancellation. Successful writes keep the same
bounded/pruning behavior. First access now uses `store_load_lock`, so concurrent
callers share one loaded cache instance.

## Currency preference and cost-store consistency

Currency preference and the main cost-store currency are two persisted stores.
Previously the preference could be saved first and the cost-store update fail,
leaving them inconsistent. Initialization had the same split-write risk.

Currency changes now:
1. serialize preference operations;
2. update the cost-store currency first;
3. persist the staged preference only after that succeeds;
4. compensate the cost-store currency back to its previous value if the
   preference save fails.

The existing selected currency rules are unchanged.

## ECB rate cache

Successful ECB refreshes previously replaced the in-memory rate table before the
storage write completed. Rate refresh and preference changes also had no shared
data-commit lock and could overwrite one another.

Rate fetches are serialized separately so the network request does not hold the
preference lock. The resulting rate table is then committed under the common
data lock using a staged copy, so preferences and rates cannot overwrite each
other. Failed storage leaves the previous rates visible.

## Regression coverage

Production-class tests cover:
- failed cost-store update leaving the preference unchanged;
- failed preference persistence rolling cost currency back;
- successful fixed-currency updates;
- failed initial auto-resolution with cost rollback;
- failed ECB-rate persistence;
- concurrent rate refresh and preference update retaining both;
- failed/cancelled online-cache records;
- failed online error-marker persistence;
- concurrent online-cache records;
- simultaneous first access creating exactly one online cache.

The General bug audit workflow now runs v208 through v213 regressions plus the
full current frontend browser suite. All other repository workflows remain
enabled.

No existing durable currency preference, price evidence, FX rates or online
cache entry is migrated or rewritten. No live Home Assistant, provider request,
camera, AI service, scale or cooker was accessed.
