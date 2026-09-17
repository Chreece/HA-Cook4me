# Cook4Me v108: shared delivery confirmation and diagnostic evidence

Build `2026.9.17.12` is cumulative from v107. It contains no recipe-specific IDs, preferred-language exception, or alternative-publication button.

## Delivery confirmation

The existing paths that verify loading (original-language delivery and replacement of a loaded recipe) now share a 90-second observation deadline. They observe connected live state and periodically request state, with one read outstanding at a time. A live confirmation interrupts a slow read. Cancellation and the deadline clean up the read task, and a stale response cannot overwrite newer cooking or disconnection evidence. Cloud acceptance and desired shadow values are not proof that the cooker loaded a recipe.

If the cloud accepts a send but the cooker does not confirm within the deadline, the result is `confirmation: unconfirmed`. The panel displays an amber pending-confirmation message instead of a rejection or verified success. The recipe is not automatically queued, resent, or added to successful-send history. Existing unrelated queue entries remain intact. Actual cloud failures remain errors. Idle mapped sends retain their existing cloud-acknowledgement behavior; this release does not claim that all sends are appliance-verified.

This behavior is shared by recipes, accounts, device locales and appliance groups. Dietary rules remain advisory for delivery, and cooking mode retains ingredient substitutions. The exact official reference IDs, original quantities and cooking programs are preserved, as are active-cooking protections.

## Firmware crash investigation

The reported appliance screen shows a native `NullPointerException` in the mobile recipe retrieval path. It does not establish the failing field or prove that language is the cause. This update does **not** fix or claim universal compatibility with that firmware. Automatically substituting a similar publication, changing an official program, or hardcoding one pudding would not resolve the general problem.

Home Assistant's integration diagnostics now include the configured locale, a limited device state snapshot, the last inspected recipe's official identity and mobile-definition structure, and up to 20 events for the latest delivery attempt. Definition evidence includes appliance groups, step types, program identifiers, parameter field names and missing program/parameter fields. Compatibility remains explicitly `unknown`. Credentials, device UUIDs, household profiles, ingredient text and raw HTTP material are not exported.

Opening any recipe's detail page collects this evidence without sending it to the cooker. Older cached details are refreshed once to obtain the structure, while a failed refresh retains the existing cached detail. Diagnostics are scoped to the selected integration entry. They allow investigation against the actual definition and firmware instead of an inferred recipe family. No per-title fallback is installed.

## Validation

- Eleven confirmation, recipe-definition and diagnostic tests pass, including delayed live updates, repeated state reads, transient failures, cancellation, stale responses, credential exclusion and refreshing an old cached detail without sending.
- Cross-language delivery tests cover unconfirmed original and mapped replacement sends, no duplicate queueing, preserved official identity and a real state-read fallback.
- Dietary guidance, runtime lifecycle and delivery/queue regression checks pass. The previously documented unrelated legacy announcement failure is not claimed fixed.
- Browser checks cover arbitrary recipe IDs, Greek/German/English messages, amber unconfirmed results, actual success and rejection, cancellation, job cleanup and mobile/desktop layouts. Foreign-recipe Send-click regression checks also pass.
- The frontend bundle is reproducible. Installer preflight includes the new confirmation/diagnostic suite and retains backup, rollback and installed-bundle verification.

Transport is simulated in the automated tests. A physical firmware crash remains unresolved until its definition/device evidence can be examined; increasing the timeout alone cannot repair a native exception.
