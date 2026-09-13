# Batch 36: exact source context for the 28 evidence requirements

Base: `0d35b270f77e5006526d52a1ef317b559b38f8ca` (PR #127 / Batch 35).

**No new nutrition bindings, semantic corrections or hold releases are approved.**
This pass investigates the saved requirements instead of substituting approximate
foods or scanning the same reference names again.

## What the retained source actually establishes

All 18 semantic-concept requirements can be joined through the existing semantic
compiler's full concept/source-local IDs to **183 reviewed source labels**. Every
member count agrees with the frozen candidate snapshot. Each source label now has
its exact language, local ingredient ID, source text, reviewed English, source
filename and byte hash, item index and original item hash in `context.json`.
These are previously reviewed source labels, not a newly retrieved provider
capture or proof of a recipe's measurement state.

The other ten requirements are provider identities. **None has an exact-key entry
in the retained provider-English review file.** A same-named semantic concept is
not substituted for it. This absence does not mean the provider ingredient is
invalid or that the complete provider capture lacks it; that capture was not
available in the supplied batch bundles.

## Concrete finding: a preparation qualifier was lost

The historical row at index 74 (zero-based) in
`release_catalog_reviewed_keyless_ingredients.v1.json` contains:

- Language: `ja`
- Source: `米(洗って30分吸水し ザルにあげる)`
- Historical reviewed English: `Rice`
- Exact ingredient ID: `local:ja:1439324e0ea7e7f84313`
- Current concept: `concept:food:d475265f55cce204989d`

The source describes rice washed, soaked for 30 minutes and drained. Its reviewed
English omits those preparation qualifiers, and the current compiler consequently
groups it with 13 other source labels under `Rice`. This is a concrete loss of
source detail, not evidence that the recipe quantity was measured after soaking.
The existing capture's exact line quantity and context are needed to investigate
that distinction. Neither dry-rice nutrition nor a water-absorption factor is
introduced. The finding is pinned in
`tools/release_catalog_nutrition_context_findings.v1.json`; its validation rejects
source, hash, index, identity or reviewed-English drift.

This batch **does not repair or split that concept**. Such a correction needs a
separate explicit semantic review and regeneration of affected memberships and
queues. The frozen candidate snapshot, historical nutrition receipts, current
28-requirement ledger and compiler behavior remain unchanged. The generic rice
target was already unapproved and remains so. The finding is not a thirteenth
historical nutrition hold.

## Context exporter

`tools/prepare_nutrition_target_context_v60.py` first runs the established full-file
hold/provenance audit. It rejects malformed semantic rows rather than silently
skipping them, proves target memberships through the existing compiler, validates
explicit findings and checks source-file fingerprints again before writing. A
changed source-file set also causes failure. No name-based join is permitted.

Without a recipe capture it produces the exact reviewed-label report above:

```sh
.venv/bin/python tools/prepare_nutrition_target_context_v60.py \
  --evidence /path/to/existing/fdc-target-candidates-offline.v60.json \
  --output /path/to/new/context-report
```

With an **already saved normalized v60 capture3 catalog** (schema 1,
`catalogVersion=2026-09-11-v60-capture3`, top-level `ingredients` and `recipes`
lists), add:

```sh
  --capture /path/to/existing/capture3-catalog.json.gz
```

Plain JSON and JSON.gz are supported. This is **not** a provider request, detail
recrawl, nutrition-cache resolver or a request for a new device capture. ZIP
bundles, raw HTTP response collections, candidate-only JSON and different catalog
versions are not accepted as normalized catalog input. The user must choose the
existing catalog explicitly; the tool does not scan home directories or choose a
capture by a similar filename. Both file and decompressed JSON are limited to
256 MiB, with duplicate JSON keys and nonfinite JSON values rejected.

For target ingredients only, `capture-context.json` retains exact global/recipe
indices, provider group/variant IDs where present, original source names/language,
quantity and unit scalars, and full original-row hashes. Provider identities
require their explicit key. Source-local recipe lines must reproduce the exact
local ID from `semanticSourceName` and `originalLanguage`. Conflicting identity
fields, missing exact globals and changed concept membership fail closed.
Repeated recipe lines are retained individually, never summed or deduplicated.
Missing lines remain missing evidence, not zero consumption. Unsupported quantity
objects are rejected, not converted or silently dropped.

Output uses an explicit field allowlist. Unknown fields, nutrient blobs,
credential fields and full recipe titles/details are not copied. Original-row
hashes cover the full rows, including omitted fields. This is not a blanket
content-redaction certificate for arbitrary text in an allowed ingredient-name
field; inspect the compact report before sharing it.

Output must be a new directory. No input is written. Exit 1 denotes invalid input
or output; **exit 2 is expected** while unresolved targets, holds or findings
remain. Report creation is not nutrition approval or activation. Only a compact
summary is printed to the terminal.

## State and validation

The 235 historical nutrition review files / 4,622 recorded IDs, 12 holds covering
22 ingredient identities, 1,697-target initial-review queue and 1,709 unresolved-
or-held total are unchanged. All 11 historical provenance discrepancies remain
visible, with none outside the hold set. The 446 older recorded targets outside
the candidate snapshot remain outside its verification scope.

The committed compressed test fixture is explicitly a subset of the 28 exact
original candidate rows. It is not a replacement for the full file. Tests cover
183 source receipts, exact IDs/member counts, the rice qualifier finding, absence
of same-name provider joins, immutable historical files, malformed/drifting
sources, capture identity checks, quantity preservation, allowed-field export,
JSON/gzip bounds, duplicate keys, nonfinite values, missing evidence, no-overwrite
behavior and source changes during extraction. Capture tests use labeled synthetic
catalogs; **the user's full capture has not been supplied or tested here**.

Full retained evidence SHA-256:
`e3b22f9b0834a79ffcc471d7bc61c07f08ce1f63da312c2ac36e84633c2931ac`.
No provider/FDC crawl, nutrient population, historical rewrite, source semantic
correction, hold removal, runtime deployment, release, catalog activation,
Home Assistant restart or live-cache change is included.
