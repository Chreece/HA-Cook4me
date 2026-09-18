# Cook4Me Touch control verification

Date: 2026-09-16. Runtime baseline: v77, commit
319a14fddb1d9eb6df39417517f4a65ff5a7481d. This change adds diagnostic tools;
it does not add device controls or require an integration update/restart.

## What the evidence establishes

| Capability | Evidence | Current conclusion |
| --- | --- | --- |
| Send an official recipe | Retained working cloud client writes the recipe IDs to the AWS IoT shadow; manufacturer documentation describes remote sending | Existing supported route |
| Monitor cooking | Historical appliance captures and the installed cookingStatus client | Existing supported route |
| Advance an ingredient step | Decompiled `xu.e.l` logs `sendOK` and calls `q71.d.h().l` with `00020303`, conditional on a connected device, matching recipe grouping and ADD_INGREDIENT step | Source-observed candidate in a BLE route; applicability to the Wi-Fi target is unverified |
| Start, pause or stop cooking | No verified command for this target in the reviewed retained evidence | Unverified |
| Change temperature, pressure or cooking time remotely | No verified command for this target in the reviewed retained evidence | Unverified |
| Change brightness/sound remotely | Brightness is documented on the appliance; cloud writable fields have not been established | Unverified |

The archived review explicitly distinguishes other appliances' heater/blade
controls from Cook4Me. Shared-app symbols cannot establish support on this target.
Earlier binary transfer traces are decompiled-source evidence, not captured
successful transfers or heating commands.

Public primary sources consulted:

- [KRUPS Cook4Me Touch](https://www.krups.de/cook4me-touch): remote recipe
  sending, recipe-book transfer and cooking monitoring.
- [Tefal CY912831 instructions and FAQ](https://www.tefal.com/instructions-for-use/csp/7211005069):
  the appliance's Settings / My device menu offers three brightness levels.

Retained source evidence reviewed (not included in the public repository):

- `cook4me-v24-reviewed-checkpoint.json`
- `cook4me-v24-offline-audit.json`
- `cook4me-binary-transfer-trace-20260905-173211.log`
- `cook4me-binary-wire-protocol-20260905-173438.log`
- `cook4me-recipe-endpoint-trace-20260905-165603.log`

## Read-only observation

Run `tools/capture_device_controls_v1.py` on the HA Docker host with `sudo python3`.
The standalone script needs no repository checkout or host Python dependencies.
It passes its own source to Python in the running `homeassistant` container and
uses the installed client plus existing cached AWS credentials. It performs no
credential refresh or persistent HA write. If credentials expire too soon, it
reports that prerequisite and still produces the available source evidence.

The observer requests only empty cookingStatus/shadow GET messages. A publish
guard refuses other topics or nonempty request payloads. It subscribes only to
the selected appliance's namespace, falling back to known exact topics when
the broker refuses wildcard subscriptions. The subscription result is recorded.

When the terminal says **Observing**, change brightness on the idle appliance,
wait about 15 seconds and restore it. Repeat for volume if that setting exists.
The default capture lasts 180 seconds. There is no need to start cooking.

The host also searches the retained decompiled app sources at
`/home/chreece/cook4me-re/jadx-phonefree/sources`. Collection is bounded to
30 seconds, 80,000 source files, 200 matching files and 12 matches per file.
Symlinks and oversized files are skipped. The result records missing/truncated
source coverage rather than assuming the whole app was reviewed.

The ZIP is written to `/home/chreece/project/cook4me/downloads` and contains only:

- `events.jsonl`: redacted subscription outcomes, settings/status structure and
  observed events. Numbers and protocol enums remain comparable. Unknown string
  values are represented by length and digest; sensitive fields are redacted.
- `app-source-clues.json`: bounded source snippets around relevant protocol terms.
- `report.json`: capture outcome, coverage limits and an explicit unverified
  remote-control conclusion.

Passwords, token files, signed URLs and raw provider stderr are not bundled.
CLI options allow choosing another container, output/source directory or
30–300 second duration. With multiple installed Cook4Me entries, `--device N`
selects one explicitly in stored config-entry order.

## Interpretation and next verification boundary

An observed setting change proves that the device reports that field. It does
not prove that a remote write is accepted or executed. A shadow update accepted
by AWS can merely store a desired value that firmware ignores. A writable
setting needs an applicable app command, the exact target/model/transport, and
physical or reported confirmation after a bounded reversible test. Absence of
events during this short capture does not prove a capability is impossible.

No real appliance capture was performed in the development workspace. The user
must run the observer on the homeserver and provide its ZIP to complete the next
evidence review.

## Validation

Seven focused tests passed: read-only publish enforcement, data redaction,
source collection, explicit device selection, subscription fallback/namespace
scope, credential timestamp parsing, and the complete host-to-container wrapper
with 500 simulated events and archive inspection. Python compilation, CLI help
and diff checks passed. The v77 baseline's GitHub Validate and Nutrition review
checkpoint workflows both passed before this diagnostic-only change.
