# Cook4Me v106: sending official editions in another language

Build `2026.9.17.10` is cumulative from v105. Its units, ingredient dropdown and announcement fallback remain included.

## Cause

The displayed error came from `_v66Send` in the v77 panel layer before any send request reached the cloud. The offline catalog supplies `sendVariantId` only when the original provider group contains an edition matching the appliance's configured language and selected yield. The Turkish soup, Bulgarian bruschetta, Romanian vegetables and Arabic porridge shown in the user's screenshot have no such match for a German-configured device.

## Behavior

The normal Send button first resolves the selected edition again for the selected device. An existing device-language mapping retains priority. If it has no mapping, Send uses the selected original official edition and marks the request for appliance-load verification. The catalog's language compatibility metadata is left intact: availability for an attempted original-language send is not presented as proven firmware compatibility.

The backend resolves the official recipe metadata, verifies the exact original ID, rechecks current dietary/allergy rules, and sends the original provider group and variant IDs using the existing cloud shadow route. Ingredient substitutions, translated UI text, portions and cooking programs are not written into a fabricated recipe. Active cooking and uncertain appliance phases retain their existing protection.

For an original-language attempt, cloud acceptance alone is insufficient. The integration waits for the selected variant in live cooking status, then reads fresh appliance state if needed. Only confirmed loading is reported as success or recorded in send history. A cloud rejection or unconfirmed load is shown as an error; the UI does not claim that every firmware supports every language.

Original-language attempts require an online cooker and are not automatically queued or retried. A failed attempt preserves unrelated queued work. Existing mapped-edition sends retain their normal offline/busy queue behavior. The UI explains original-language success, offline requirements and unconfirmed loading in Greek, German and English.

## Verification and limits

- Eight new Python tests cover the four real catalog editions, exact IDs and unchanged recipes, delayed live status, fresh state confirmation, cloud acknowledgement without loading, offline requests, active cooking, mismatched IDs, authoritative dietary checks, cloud rejection and cancellation.
- Seven existing diet-send tests, 25 lifecycle/queue tests and seven catalog identity tests pass.
- Chromium exercises actual Send button clicks for all four editions, preserved portions and ingredients, mapped-edition preference and queueing, target/filter scoping, stale and blocked selections, and localized unconfirmed-load errors.
- Frontend bundle reproduction, JavaScript syntax, Python compilation and whitespace checks pass.
- Tests simulate cloud/device transport. Acceptance by the user's firmware and its displayed language require a live Send attempt after installation. An unconfirmed load does not prove a language rejection: the device could also be slow, disconnected or awaiting an on-screen interaction.

Use the pinned v106 installer. It retains the backup, 120-second Home Assistant stop timeout, activation check and rollback behavior, and adds the original-language delivery tests to preflight.

Published runtime: `dd8c369d0eae3bcd287631b25fc228bbfd162a43` on `cook4me-original-language-v106`. Its tree matches the tested local source: `0e174df746f71abf13f300d660fe8ea4ed692033`.

The four v106 installer tests also pass, covering successful backup/activation, invalid or missing staged data, and rollback after activation failures. Total focused Python validation: **51 passing tests**, plus the Chromium send-flow suite. No live appliance send was performed during development.
