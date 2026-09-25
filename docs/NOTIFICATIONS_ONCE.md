# Cook4Me Home Assistant notifications

Cook4Me uses one Home Assistant persistent-notification ID per category and
config entry: upcoming expiry, consumed-ingredient confirmation and AI recipe
generation. All producers now use `Cook4MeNotifications`.

The entry's notification ledger remembers event identities in Home Assistant
storage. It contains no notification message, recipe title or food name: expiry
and consumption identities are hashed, and AI requests use random identifiers.
The ledger loads before device listeners and the initial inventory check run.
Writes are delayed/coalesced, flushed by HA on shutdown and explicitly flushed
after bridge tasks stop on entry unload. Closing the manager is idempotent.

## Expiry warnings

- A product and its effective use date receive one warning. Quantity, storage,
  list order, countdown text and regenerated legacy lot IDs do not create a new
  warning. Several batches of that product with the same date share its warning
  identity; their details still appear together in one notification.
- Opening-package limits participate through the same effective use date.
- Dismiss and dismiss-all suppress the warning. Inventory edits, the next day's
  check, temporary removal/reappearance, entry reload and HA restart do not
  reopen it.
- A newly warned product or a different effective use date may create one new
  notification. Previously dismissed products are excluded from that message.
- An unread notification can include newly warned products and remove consumed
  products. Only one notification is visible for that inventory. After all its
  products disappear, the notification is removed.
- The message lists up to 40 batches and reports how many additional batches
  are included. Dismissing it acknowledges the full group.

The expiry list inside Cook4Me remains available independently of notification
dismissal. Dismissing an alert does not change inventory or expiry priority.

## Other notifications

Each consumption confirmation is keyed by its pending-confirmation ID. Device
done packets, active-flag changes, reconnects, startup snapshots and transitions
through keep-warm cannot create another confirmation for the same observed cook.
A subsequent cooking cycle can create a new confirmation.

Each explicit AI-generation request has its own event ID. Running, completed
and failed messages update that request's existing notification. If the user
dismisses the running notification, neither completion nor failure brings it
back. WebSocket results/errors still reach the requesting UI. A new explicit
request may notify again; a late update cannot overwrite a newer request.

Dismissal is observed through HA's `persistent_notification.async_register_callback`
and `UpdateType.REMOVED`, including dismiss-all. These interfaces were verified
against HA 2026.3.0 (the integration minimum) and 2026.9.0. Active-message state
is session-local, so old status updates cannot resurrect previously delivered
notifications after restart. Notification history created before this feature
cannot be reconstructed; the ledger starts with the first check after updating.

This applies to Cook4Me's Home Assistant persistent notifications. Other
integrations' notifications and Cook4Me's optional spoken announcements retain
their existing behavior.

## Validation

`python tests/test_notifications_once.py` exercises the real expiry and inventory
code, shared manager, both AI endpoint handlers, completion listener and
consumption notification producer. It covers dismissal, dismiss-all, subsequent
days, stock edits, new warnings, opened-package dates, overflow, legacy IDs,
entry isolation, reload/restart, late results, setup failures and task cleanup.
An AST audit prevents another Python producer from bypassing the shared manager.
The suite runs in the Validate CI workflow.
