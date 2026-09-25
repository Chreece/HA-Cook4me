# Product save responsiveness

Saving a reviewed barcode product no longer waits behind unrelated queued
Cook4Me requests. The shared frontend request queue could otherwise hold Save
until an AI request, online lookup or device operation completed. The save
still passes through the existing validation, cache and transport layers.

Each product save owns its progress job. Cancelling background work does not
cancel the save. The server's scanner and inventory locks continue to protect
concurrent writes. Success is shown only after the server acknowledges the
save; double taps remain guarded and uncertain results retain the edited draft
and frozen request for retry.

Transport job IDs are excluded from the product fingerprint. A retry with a
new job ID can therefore replay its durable receipt without adding stock
again. A changed product cannot reuse a committed request ID. Barcode,
nutrition and price persistence retain their existing behavior.

Runtime v224 loads the updated compiled legacy layers and retains the seasonal
ingredient filter. The bundle builder now overlays the edited queue and job
sources so regeneration preserves the fix.

Local verification uses the actual frontend graph at 390px and 1440px with a
deliberately blocked background request, followed by barcode lookup, editing,
save, repeated taps, a lost reply and retry. The regression failed before the
fix because Save never reached transport. It now passes while background work
remains blocked, including when that work is cancelled. Backend tests exercise
the production handler and durable ledger for retries, changed payloads,
failed storage and concurrent duplicate requests. Home Assistant's actual
storage and network latency are not measured by these isolated tests.
