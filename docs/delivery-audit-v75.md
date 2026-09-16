# Cook4Me delivery and persistence audit — v75

This follow-up retains v74 and fixes five additional runtime failure modes.

- A queued recipe cancelled or replaced while metadata is loading, or while
  waiting behind another send, is rechecked under the send lock before dispatch.
  This does not recall a command that has already been submitted to the cooker.
- Recipe-book mutations use a separate candidate snapshot and publish it only
  after storage succeeds. Failed or cancelled saves leave the committed
  favourites, recipe list and deferred-send state intact. Background queue
  processing cannot observe an unsaved replacement as a committed request.
- A failed dashboard status subscriber is removed without interrupting speech
  delivery, other subscribers, or announcements for other users.
- A cooking-state announcement delayed by AI or another speaker operation is
  discarded if the appliance disconnects or the active recipe changes.
- Entity consolidation and announcement preference writes share a lock, so the
  migration cannot overwrite a concurrent user's saved settings.

`tests/test_delivery_audit_v75.py` reproduces the original failures and tests the
actual runtime methods with cloud, storage and speaker I/O isolated. It also
checks that an unchanged queued recipe still sends and clears normally. Existing
v74 runtime and v72 announcement tests cover successful delivery and permissions.

The v75 installer runs the new regression checks before replacing Cook4Me and
keeps the existing backup, rollback and post-restart verification. The frontend
remains the tested v74 build because this update changes backend behavior.
Live appliance and speaker verification still needs the user's Home Assistant.
